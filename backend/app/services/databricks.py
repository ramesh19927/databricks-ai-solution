from typing import Dict, Iterable, List

from databricks.sdk import WorkspaceClient


class DatabricksIngestionService:
    def __init__(self, host: str, token: str, http_path: str | None = None, warehouse_id: str | None = None) -> None:
        self.client = WorkspaceClient(host=host, token=token)
        self.http_path = http_path
        self.warehouse_id = warehouse_id

    def fetch_table_sample(self, table: str, limit: int = 50) -> List[Dict[str, str]]:
        """Fetch a sample of rows from a Unity Catalog table or SQL warehouse."""
        statement = f"SELECT * FROM {table} LIMIT {limit}"
        result = self.client.statement_execution.execute_statement(
            statement=statement,
            warehouse_id=self.warehouse_id,
            wait_timeout=60,
        )
        rows: List[Dict[str, str]] = []
        if not result.result or not result.result.data_array:
            return rows
        for row in result.result.data_array:
            as_dict = {}
            for idx, col in enumerate(result.result.manifest.columns):
                as_dict[col.name] = str(row[idx])
            rows.append(as_dict)
        return rows

    def fetch_dbfs_file(self, path: str) -> Iterable[Dict[str, str]]:
        """Stream lines from a DBFS file path."""
        content = self.client.dbfs.read(path)
        decoded = content.data.decode("utf-8")
        for idx, line in enumerate(decoded.splitlines()):
            yield {"line": str(idx + 1), "content": line}
