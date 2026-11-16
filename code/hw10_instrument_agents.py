"""One-time HW10 tracing instrumentation for existing Kafka agents."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

IMPORT = (
    "from hw10_tracing import "
    "trace_stage, record_kafka_queue_wait\n"
)


def add_import(source):
    marker = "from kafka import KafkaConsumer, KafkaProducer\n"
    assert source.count(marker) == 1
    assert IMPORT not in source
    return source.replace(marker, marker + IMPORT, 1)


def indent_block(block):
    return "".join(
        "    " + line if line.strip() else line
        for line in block.splitlines(keepends=True)
    )


def wrap_block(source, start, end, wrapper):
    assert start in source, f"Missing start: {start}"
    assert end in source, f"Missing end: {end}"

    first = source.index(start)
    last = source.index(end, first)

    original = source[first:last]

    return (
        source[:first]
        + wrapper
        + indent_block(original)
        + source[last:]
    )


# PLANNER
path = ROOT / "planner.py"
source = add_import(path.read_text())

marker = '        question = request["question"]\n'
assert source.count(marker) == 1

source = source.replace(
    marker,
    (
        "        record_kafka_queue_wait(\n"
        "            message, correlation_id, 'planner'\n"
        "        )\n"
        + marker
    ),
    1,
)

source = wrap_block(
    source,
    '        question = request["question"]\n',
    "        consumer.commit()\n",
    (
        "        with trace_stage(\n"
        "            correlation_id, 'planner',\n"
        "            input_topic=INPUT_TOPIC,\n"
        "            output_topic=OUTPUT_TOPIC,\n"
        "        ):\n"
    ),
)

path.write_text(source)
print("PASS: Planner instrumented")


# WRITER
path = ROOT / "writer.py"
source = add_import(path.read_text())

marker = "        # Part 3.I: Skip previously processed tasks."
assert source.count(marker) == 1

source = source.replace(
    marker,
    (
        "        record_kafka_queue_wait(\n"
        "            message, correlation_id, 'writer'\n"
        "        )\n\n"
        + marker
    ),
    1,
)

source = wrap_block(
    source,
    "                draft = create_draft(task)\n",
    "            except (KeyError, TypeError, ValueError) as error:\n",
    (
        "                with trace_stage(\n"
        "                    correlation_id, 'writer',\n"
        "                    attempt=attempt,\n"
        "                    input_topic=INPUT_TOPIC,\n"
        "                    output_topic=OUTPUT_TOPIC,\n"
        "                ):\n"
    ),
)

dead_letter_send = """                    producer.send(
                        DEAD_LETTER_TOPIC,
                        value=dead_letter,
                    ).get(timeout=15)"""

assert source.count(dead_letter_send) == 1

source = source.replace(
    dead_letter_send,
    (
        "                    with trace_stage(\n"
        "                        correlation_id, 'dead_letter_publish',\n"
        "                        output_topic=DEAD_LETTER_TOPIC,\n"
        "                    ):\n"
        + indent_block(dead_letter_send)
    ),
    1,
)

path.write_text(source)
print("PASS: Writer instrumented")


# REVIEWER
path = ROOT / "reviewer.py"
source = add_import(path.read_text())

marker = '        draft = draft_message["draft"]\n'
assert source.count(marker) == 1

source = source.replace(
    marker,
    (
        "        record_kafka_queue_wait(\n"
        "            message, correlation_id, 'reviewer'\n"
        "        )\n"
        + marker
    ),
    1,
)

source = wrap_block(
    source,
    '        draft = draft_message["draft"]\n',
    "        consumer.commit()\n",
    (
        "        with trace_stage(\n"
        "            correlation_id, 'reviewer',\n"
        "            input_topic=INPUT_TOPIC,\n"
        "            output_topic=OUTPUT_TOPIC,\n"
        "        ):\n"
    ),
)

path.write_text(source)
print("PASS: Reviewer instrumented")
