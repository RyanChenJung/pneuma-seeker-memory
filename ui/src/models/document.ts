export interface AbstractDocument {
    doc_id: string;
    retriever_type: string;
    content: any;
    metadata: Record<string, string>
}
