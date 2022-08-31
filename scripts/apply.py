from yoyo import read_migrations, get_backend

backend = get_backend('postgres://postgres:@localhost:5432/market_app_database')
migrations = read_migrations('./migrations')
backend.apply_migrations(backend.to_apply(migrations))