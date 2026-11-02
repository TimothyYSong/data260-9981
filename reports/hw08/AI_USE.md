# DATA 260 — Homework 8 AI Use Disclosure

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT to help interpret the HW8 instructions, plan implementation steps, draft and review Python/Kafka code, troubleshoot Docker and Kafka CLI commands, and organize the required report, logs, and results tables. This included guidance for the inspection request/response service, the Planner → Writer → Reviewer pipeline, and the four Part 3 failure experiments.

I ran the commands in my own development environment, edited and saved the source files, started and stopped the Kafka/worker containers, carried out the CREATE/GET and failure tests, checked the actual terminal output, and captured the report evidence. I checked results against the assignment handout and saved the real logs and CSV outputs under `reports/hw08/`.

## 2. What was one AI-produced output that was wrong or unsuitable, or one result you independently verified?

An AI-suggested Kafka consumer-group inspection command used `kafka-consumer-groups.sh` without its absolute path inside the Kafka container. That command did not run because the executable was not in the container's `PATH`.

## 3. How did you detect or verify the problem?

I executed the suggested command and observed the actual error: `exec: "kafka-consumer-groups.sh": executable file not found in $PATH`. I then ran the corrected command and inspected the consumer-group table rather than relying on the AI's predicted output. The table showed both `s9981_tasks` partitions caught up: partition 0 current/end offsets `16/16` and partition 1 `33/33`, with lag `0` on each.

## 4. What did you change, and why does it work now?

I used the executable's full path, `/opt/kafka/bin/kafka-consumer-groups.sh`, with the same bootstrap server and consumer group:

```bash
docker compose exec -T kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:19092 \
  --group s9981_writers \
  --describe
```

The corrected command ran successfully because it addressed the script at its actual location in the container. It provided objective offset and lag evidence for the saved HW8 records. This was a CLI invocation correction; it did not require changing the Kafka application logic.

---

**Evidence:** `reports/hw08/RUN_LOG.txt`, `reports/hw08/raw/part3_consumer_offsets_final.txt`, and the Part 1–3 experiment records in `reports/hw08/raw/`. AI guidance was checked against observed program output; no unexecuted command was represented as a successful test.
