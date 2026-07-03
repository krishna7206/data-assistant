from dataclasses import dataclass, field
from sqlalchemy import create_engine, inspect, text

@dataclass
class ColumnMeta:
    name: str
    dtype: str
    nullable: bool
    primary_key: bool

@dataclass
class TableMeta:
    name: str
    schema: str = "dbo"              # add this line
    columns: list[ColumnMeta] = field(default_factory=list)
    row_count: int | None = None

@dataclass
class SchemaRegistry:
    tables: list[TableMeta] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        lines = []
        for table in self.tables:
            lines.append(f"Table: {table.schema}.{table.name} ({table.row_count} rows)")
            for col in table.columns:
                pk = " PK" if col.primary_key else ""
                lines.append(f"  {col.name} ({col.dtype}){pk}")
        return "\n".join(lines)
        

def normalise_type(raw: str) -> str:
    raw = raw.lower()
    if "int" in raw:
        return "integer"
    if "varchar" in raw or "char" in raw or "text" in raw:
        return "text"
    if "decimal" in raw or "numeric" in raw or "float" in raw:
        return "numeric"
    if "datetime" in raw or "timestamp" in raw:
        return "timestamp"
    if "date" in raw:
        return "date"
    if "bit" in raw or "bool" in raw:
        return "boolean"
    return raw


def extract(engine):
    insp = inspect(engine)

    system_schemas = {
        "information_schema", "sys", "guest", "INFORMATION_SCHEMA",
        "db_accessadmin", "db_backupoperator", "db_datareader",
        "db_datawriter", "db_ddladmin", "db_denydatareader",
        "db_denydatawriter", "db_owner", "db_securityadmin"
    }
    schemas = [s for s in insp.get_schema_names() if s not in system_schemas]

    tables = []
    for schema in schemas:
        for table_name in insp.get_table_names(schema=schema):

            # primary keys
            pk_info = insp.get_pk_constraint(table_name, schema=schema)
            pk_cols = set(pk_info.get("constrained_columns", []))

            # columns
            columns = []
            for col in insp.get_columns(table_name, schema=schema):
                columns.append(ColumnMeta(
                    name=col["name"],
                    dtype=normalise_type(str(col["type"])),
                    nullable=col["nullable"],
                    primary_key=col["name"] in pk_cols,
                ))

            # row count
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'))
                row_count = result.scalar()

            tables.append(TableMeta(name=table_name, schema=schema, columns=columns, row_count=row_count))

    return SchemaRegistry(tables=tables)


