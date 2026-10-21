# CronDaemon

CronDaemon is an automated study-guide generator that selects a subtopic for each technical subject, generates study notes, compiles them into a PDF, and optionally emails the guide.

Designed for personal learning and daily technical revision.

## Features

- Selects subtopics from configured technical subjects.
- Generates structured study notes.
- Compiles notes into a PDF study guide.
- Supports optional email delivery.
- Allows running for a specific day or subject.

## Usage

Run locally without sending an email:

```bash
python src/main.py --no-mail --day 1 --only Docker
```

Run the test suite:

```bash
pytest -q
```

## Intended Use

For personal educational use. Ensure that external references and source materials are used in accordance with their licenses and terms of service.
