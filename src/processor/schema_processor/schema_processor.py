from ast import literal_eval
from pandas import DataFrame
from processor.llm.interface.model_interface import ModelInterface
from processor.llm.interface.model_factory import get_model
from processor.llm.prompts import schema_enhancer_prompts
from processor.utils import format_schema_with_samples
from tqdm import tqdm
from processor.types.message import Message

class SchemaProcessor:
    def __init__(self, ckp: str):
        model_interface = get_model(ckp)
        self.model: ModelInterface = model_interface(ckp)
        self.model.load_model()
        self.model.load_tokenizer()
    
    def get_enhanced_schema(self, tables: list[DataFrame]) -> list[str]:
        results = []
        for table in tqdm(tables):
            # Step 1: Determine what the table represents
            table_description = self.__get_table_description(table)
            print(f'=> Schema description: {table_description}')

            # Step 2: Rename each column
            new_columns: list[str] = []
            print(f"=> Overall schema: {table.columns}")
            for col in table.columns:
                new_col_reason_and_name = self.__rename_column(table, col, table_description)
                new_col_name = new_col_reason_and_name.split('New column name:')[-1].strip()
                new_col_name = new_col_name.split(':')[0]
                if new_col_name.endswith('\n'):
                    new_col_name = new_col_name.split('\n')[0]
                print(f"==> Reasoning: {new_col_reason_and_name}")
                print(f"==> Renaming column {col} to {new_col_name}")
                new_columns.append(new_col_name)
            results.append(new_columns)
        return results
    
    def __get_table_description(self, table: DataFrame, sample = 3):
        table_desc_samples: list[str] = []
        for i in range(sample):
            msg: list[Message] = [
                {'role': 'system', 'content': schema_enhancer_prompts['table_descriptor']},
                {'role': 'user', 'content': format_schema_with_samples(table, 3, 42+i) },
            ]
            table_desc_sample = self.model.chat(msg)
            table_desc_samples.append(table_desc_sample)

        # Now combine them
        all_descs = ""
        for j in range(len(table_desc_samples)):
            all_descs += f'Description {j}: {table_desc_samples[j]}\n'
        all_descs = all_descs.strip()
        msg: list[Message] = [
            {'role': 'system', 'content': schema_enhancer_prompts['description_combinator']},
            {'role': 'user', 'content': all_descs },
        ]
        table_description = self.model.chat(msg)
        print(f"==> Sample descriptions: {table_desc_samples}")
        print(f"==> Table description: {table_description}")
        return table_description

    def __rename_column(self, table: DataFrame, col_name: str, table_desc: str):
        msg: list[Message] = [
            {'role': 'system', 'content': schema_enhancer_prompts['column_renamer']},
            {'role': 'user', 'content': f'- Schema: {format_schema_with_samples(table)}\n\n- Description: {table_desc}\n\n- Column to be renamed: {col_name}' },
        ]
        new_col_name = self.model.chat(msg)
        return new_col_name

    def get_target_schema(self, question: str) -> list[str]:
        messages = [
            {"role": "system", "content": 'schema_generator_system_prompt'},
            {"role": "user", "content": f"Question: {question}"}
        ]
        target_schema = self.model.chat(messages)
        try:
            target_schema = literal_eval(target_schema)
            return target_schema
        except:
            return []
