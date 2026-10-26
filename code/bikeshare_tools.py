"""DATA 260 HW7 Part 4: Bay Wheels MRKL tools."""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import sqlglot
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlglot import exp


class CsvSqlInput(BaseModel):
    """JSON schema for the csv_sql tool."""

    sql: str = Field(
        description="One read-only SELECT query against the trips table"
    )


def create_csv_sql_tool(csv_path: str):
    """Create a read-only SQL tool for one uploaded CSV."""

    path = Path(csv_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")

    conn = duckdb.connect(":memory:")

    conn.execute(
        "CREATE TABLE trips AS SELECT * FROM read_csv_auto(?)",
        [str(path)],
    )

    # Prevent SQL from accessing external files or URLs.
    conn.execute("SET enable_external_access = false")

    @tool("csv_sql", args_schema=CsvSqlInput)
    def csv_sql(sql: str) -> dict:
        """Run a single read-only SELECT query against uploaded trip data."""

        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            statements = sqlglot.parse(sql, read="duckdb")

            if len(statements) != 1:
                raise ValueError("Exactly one SQL statement is required.")

            statement = statements[0]

            if not isinstance(statement, exp.Select):
                raise ValueError("Only SELECT queries are permitted.")

            prohibited = (
                exp.Command,
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Drop,
                exp.Create,
                exp.Alter,
                exp.Copy,
                exp.Into,
            )

            for node in statement.walk():
                if isinstance(node, prohibited):
                    raise ValueError("Prohibited SQL operation.")

                if isinstance(node, exp.Table):
                    if (
                        node.name.lower() != "trips"
                        or node.db
                        or node.catalog
                    ):
                        raise ValueError(
                            "Only the uploaded trips table is allowed."
                        )

                if isinstance(node, exp.Anonymous):
                    if node.name.upper() in {
                        "READ_CSV",
                        "READ_CSV_AUTO",
                        "READ_PARQUET",
                        "SQLITE_SCAN",
                    }:
                        raise ValueError(
                            "External data functions are blocked."
                        )

            safe_sql = (
                "SELECT * FROM ("
                + statement.sql(dialect="duckdb")
                + ") AS safe_result LIMIT 100"
            )

            # Use an independent DuckDB cursor for each tool call.
            cursor = conn.cursor()
            try:
                cursor.execute(safe_sql)
                columns = [col[0] for col in cursor.description]
                rows = [
                    dict(zip(columns, record))
                    for record in cursor.fetchall()
                ]
            finally:
                cursor.close()

            rows = json.loads(json.dumps(rows, default=str))

            return {
                "success": True,
                "data": {
                    "rows": rows,
                    "row_count": len(rows),
                    "source": "uploaded.csv",
                },
                "source": "uploaded.csv",
                "ts": timestamp,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "source": "uploaded.csv",
                "ts": timestamp,
            }

    return csv_sql


class PolicyRetrieverInput(BaseModel):
    """JSON schema for the pricing-policy retriever."""

    url: str = Field(description="Official Bay Wheels pricing-page URL")
    query: str = Field(description="Pricing information to retrieve")
    k: int = Field(default=5, ge=1, le=10)


def create_policy_retriever_tool():
    """Create an official-pricing-page retrieval tool."""
    import hashlib
    import re
    from urllib.parse import urlparse

    import requests
    from bs4 import BeautifulSoup

    @tool("policy_retriever", args_schema=PolicyRetrieverInput)
    def policy_retriever(url: str, query: str, k: int = 5) -> dict:
        """Fetch Bay Wheels pricing and return relevant quotable passages."""
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            parsed = urlparse(url)

            if (
                parsed.scheme != "https"
                or parsed.hostname != "lyftbikes.com"
                or parsed.path.rstrip("/") != "/pricing"
                or parsed.username
                or parsed.password
                or parsed.port
            ):
                raise ValueError(
                    "Only https://lyftbikes.com/pricing is permitted."
                )

            response = requests.get(
                "https://lyftbikes.com/pricing",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
                allow_redirects=False,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            # This exact extracted text can be saved as evidence later.
            snapshot = " ".join(soup.stripped_strings)
            if not snapshot:
                raise ValueError("Pricing page contained no readable text.")

            snapshot_hash = hashlib.sha256(
                snapshot.encode("utf-8")
            ).hexdigest()

            # Use overlapping passages to retain pricing-table context.
            words = snapshot.split()
            window = 45
            stride = 25
            chunks = [
                " ".join(words[i:i + window])
                for i in range(0, len(words), stride)
            ]

            tokens = set(
                re.findall(r"[a-z0-9]+", query.lower())
            )
            tokens -= {
                "the", "and", "for", "with", "what",
                "are", "how", "much", "does", "cost",
            }

            ranked = []
            for index, chunk in enumerate(chunks):
                lower = chunk.lower()
                matches = sum(
                    1 for token in tokens if token in lower
                )
                pricing_bonus = sum(
                    1 for term in (
                        "$", "/min", "month", "unlock",
                        "classic", "ebike", "45 min",
                    )
                    if term in lower
                )
                score = matches * 10 + pricing_bonus
                ranked.append((score, index, chunk))

            ranked.sort(key=lambda item: (-item[0], item[1]))

            passages = [
                {
                    "text": chunk,
                    "source": "https://lyftbikes.com/pricing",
                    "score": float(score),
                }
                for score, _, chunk in ranked[:k]
            ]

            return {
                "success": True,
                "data": {
                    "passages": passages,
                    "snapshot_text": snapshot,
                    "snapshot_sha256": snapshot_hash,
                    "accessed_at": timestamp,
                    "url": "https://lyftbikes.com/pricing",
                },
                "source": "https://lyftbikes.com/pricing",
                "ts": timestamp,
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "source": url,
                "ts": timestamp,
            }

    return policy_retriever


class CalculatorInput(BaseModel):
    """JSON schema for the calculator tool."""

    expression: str = Field(
        description="Arithmetic expression containing only numbers and + - * / ( ) ."
    )
    units: str | None = Field(
        default=None,
        description="Optional output units, such as USD or rides"
    )


def create_calculator_tool():
    """Create a safe arithmetic calculator without eval."""
    import ast
    import math
    import operator
    import re

    allowed_pattern = re.compile(r"^[0-9+\-*/().\s]+$")

    binary_operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    unary_operations = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise ValueError("Only numeric constants are allowed.")
            return node.value

        if isinstance(node, ast.BinOp):
            operation = binary_operations.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported arithmetic operator.")

            left = evaluate(node.left)
            right = evaluate(node.right)
            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            operation = unary_operations.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported unary operator.")
            return operation(evaluate(node.operand))

        raise ValueError("Unsupported expression.")

    @tool("calculator", args_schema=CalculatorInput)
    def calculator(expression: str, units: str | None = None) -> dict:
        """Safely calculate arithmetic expressions without eval."""
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            if (
                not expression
                or len(expression) > 200
                or not allowed_pattern.fullmatch(expression)
            ):
                raise ValueError(
                    "Expression violates the arithmetic whitelist."
                )

            tree = ast.parse(expression, mode="eval")
            value = evaluate(tree)

            if not math.isfinite(value):
                raise ValueError("Result must be finite.")

            if abs(value) > 1e12:
                raise ValueError("Result exceeds the allowed range.")

            data = {"value": float(value)}

            if units is not None:
                data["units"] = units

            return {
                "success": True,
                "data": data,
                "source": "calculator",
                "ts": timestamp,
            }

        except (Exception) as exc:
            return {
                "success": False,
                "error": str(exc),
                "source": "calculator",
                "ts": timestamp,
            }

    return calculator
