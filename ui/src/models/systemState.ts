import { AbstractDocument } from "./document";

export interface SystemState {
  target_schemas: Record<string, any>; // Replace 'any' if you know DataFrame's JSON format
  is_target_schemas_materialized: boolean;
  column_descriptions: Record<string, Record<string, string>>;
  sqls: string[];
  is_sql_executed: boolean;
  curr_retrieval_results: Partial<Record<string, AbstractDocument[]>>
}
