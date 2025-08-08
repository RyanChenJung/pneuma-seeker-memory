export type Sender = "user" | "assistant";

export interface Message {
  sender: Sender;
  text: string;
}
