run:
    @uv run manage.py runserver_plus

sh:
    @uv run manage.py shell_plus

test:
    uv run coverage run manage.py test --parallel
    uv run coverage combine
    uv run coverage report

docker-build IMAGE='fullsite':
    docker build --tag {{IMAGE}} .

docker-test IMAGE='fullsite': docker-build
    docker run --rm --env-file .env.example {{IMAGE}} python manage.py test --parallel
