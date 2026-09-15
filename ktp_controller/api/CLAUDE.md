# API coding conventions

All SQLAlchemy ORM models: @ktp_controller/api/models.py

All endpoints: @ktp_controller/api/*/routes.py

All endpoints use POST method, the final part of the path is a
verb. e.g. `POST /api/v1/exam/get_curent_exam_package`.

Endpoint function name is the verb prefixed with a single underscore,
e.g. _get_current_exam_package.
