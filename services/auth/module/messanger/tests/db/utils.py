
def obtain_schema_from_table_args(table_args: tuple):
  for arg in table_args:
    if isinstance(arg, dict):
      if "schema" in arg:
        return arg["schema"]
  assert False, "Shema was not found in table args"
