// models/systemState.ts
import { AbstractDocument } from "./document";

export interface SystemState {
  T: Record<string, any>; // Replace 'any' if you know DataFrame's JSON format
  is_T_materialized: boolean;
  column_descriptions: Record<string, Record<string, string>>;
  Q: string[];
  is_Q_executed: boolean;
  curr_retrieval_results: Partial<Record<string, AbstractDocument[]>>
}
