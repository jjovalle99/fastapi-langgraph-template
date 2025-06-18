from pydantic import BaseModel, SecretStr


class DatabaseConfig(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: SecretStr
    schema_name: str = "{{ project_slug }}"

    @property
    def connection_string(self) -> str:
        return (
            f"dbname={self.database} user={self.user} password={self.password.get_secret_value()} host={self.host} port={self.port} "
            f"options='-c search_path={self.schema_name},public'"
        )
