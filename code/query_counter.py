from contextvars import ContextVar

from sqlalchemy import event

from database import engine


query_counter = ContextVar("query_counter", default=None)


@event.listens_for(engine, "before_cursor_execute")
def count_query(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany,
):
    counter = query_counter.get()

    if counter is not None:
        counter["count"] += 1