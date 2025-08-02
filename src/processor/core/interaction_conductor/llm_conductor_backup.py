#                 self.logger.info("Check if safe to run the SQL queries on the (materialized) target schemas")
#                 if (
#                     len(self.info_need_state.target_schemas.keys()) > 0
#                     and self.info_need_state.is_target_schemas_materialized
#                 ):
#                     for sql in sqls:
#                         relevant_table_ids = [
#                             i
#                             for i in self.info_need_state.target_schemas.keys()
#                             if i in sql
#                         ]
#                         for relevant_table_id in relevant_table_ids:
#                             validation_messages = [
#                                 LLMMessage(
#                                     role=Role.SYSTEM.value,
#                                     content="""You will receive an actual table and SQL query. Your task is to validate and transform the EXISTING table values to match the SQL query requirements.

# Example scenario:
# - If SQL has: WHERE status = 'ACTIVE'
# - But table has: status values like 'active' or 'Active'
# - You should transform to match case: df['status'] = df['status'].str.upper()

# Rules for Python code:
# 1. Work ONLY with the provided table - do not create hypothetical scenarios
# 2. Use the actual table from tables["<table_id>"] dictionary
# 3. Transform values to match SQL requirements (case, format, etc.)
# 4. Return transformed DataFrame in 'result' variable
# 5. Available libraries: pandas (as pd) and numpy (as np)

# Output only the Python code needed for transformation. If no changes needed, use:
# result = tables["<table_id>"]""",
#                                 ),
#                                 LLMMessage(
#                                     role=Role.USER.value,
#                                     content=f"""The SQL query: ```{sql}```\n\nThe ACTUAL table content: ```{self.info_need_state.get_table_repr(self.info_need_state.target_schemas[relevant_table_id], relevant_table_id)}```""",
#                                 ),
#                             ]
#                             code = parse_code(self.llm.chat(validation_messages))
#                             resulting_table = execute_python_code(
#                                 code,
#                                 {
#                                     relevant_table_id: self.info_need_state.target_schemas[
#                                         relevant_table_id
#                                     ]
#                                 },
#                                 self.logger,
#                             )
#                             if isinstance(resulting_table, DataFrame):
#                                 self.info_need_state.target_schemas[
#                                     relevant_table_id
#                                 ] = resulting_table