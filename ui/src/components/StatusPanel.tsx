// components/StatusPanel.tsx (need massive changes)
"use client";

import { useEffect, useState } from "react";
import { PanelRightOpen } from "lucide-react";
import { MessageFormat } from "../models/message";
import { SystemState } from "@/models/systemState";

interface Props {
  messages: MessageFormat[];
  visible: boolean;
  onToggleStatus: () => void;
}

const exampleFilledState = {
  T: {},
  is_T_materialized: false,
  column_descriptions: {
    "table_1": {
      "col_1": "Description of col_1",
      "col_2": "Description of col_2",
    },
    "table_2": {
      "col_3": "Description of col_3",
      "col_4": "Description of col_4",
    },
  },
  Q: [],
  is_Q_executed: false,
  curr_retrieval_results: {},
}

export default function StatusPanel({ messages, visible, onToggleStatus }: Props) {
  const [systemState, setSystemState] = useState<SystemState>(exampleFilledState);

  // useEffect(() => {
  //   if (visible) {
  //     getState()
  //       .then(setSystemState)
  //       .catch(console.error);
  //   }
  // }, [visible]); // only run when 'visible' changes to true

  return (
    <aside
      className={`
        relative bg-white border-gray-300 flex flex-col transition-all duration-500 ease-in-out overflow-hidden
        ${visible
          ? "md:max-w-[33%] max-w-full border-r md:border-r border-b md:border-b-0 p-6"
          : "max-w-0 border-0 p-0"}
      `}
      style={{ minWidth: 0 }}
    >
      {visible && (
        <>
          <button
            onClick={onToggleStatus}
            aria-label="Hide Status Panel"
            className="absolute top-2 right-2 px-3 py-1 rounded bg-[#800000] cursor-pointer text-white hover:bg-[#510400] transition"
          >
            <PanelRightOpen />
          </button>

          <h2 className="text-xl font-semibold mb-4">System's State</h2>
          <div className="flex-grow overflow-auto">
            <p className="mb-2"><strong>S ({systemState.is_T_materialized ? "Materialized" : "Not yet Materialized"}):</strong> {JSON.stringify(systemState.T)}</p>
            <p className="mb-2"><strong>Column Descriptions:</strong></p>
            <ul>
              {Object.entries(systemState.column_descriptions).map(([key, value]) => (
                <li key={key} className="mb-2">
                  <strong>{key}:</strong>
                  <ul>
                    {Object.entries(value).map(([key2, value2]) => (
                      <li key={key2}>
                        - {key2}: {value2}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
            <p className="mb-2"><strong>Q ({systemState.is_Q_executed ? "Executed" : "Not yet Executed"}):</strong> {JSON.stringify(systemState.Q)}</p>
            <p className="mb-2"><strong>Currently Retrieved Documents</strong> {JSON.stringify(systemState.curr_retrieval_results)}</p>
          </div>
        </>
      )}
    </aside>
  );
}
