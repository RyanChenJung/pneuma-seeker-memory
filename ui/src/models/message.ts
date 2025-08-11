export interface MessageFormat {
  text: string;
  sender: "assistant" | "user" | "log";
  time_stamp: number;
}
