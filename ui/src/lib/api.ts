// lib/api.ts
import axios from "axios";

const BASE_URL = "http://localhost:8000";

/** Get all users */
export async function getAllUsers(): Promise<string[]> {
  const res = await axios.get<{ users: string[] }>(`${BASE_URL}/users`);
  return res.data.users;
}

/** Register a user */
export async function registerUser(userId: string): Promise<boolean> {
  const res = await axios.post(`${BASE_URL}/users/register`, {
    user_id: userId,
  });
  return res.data.status === "ok";
}

/** Delete a user */
export async function deleteUser(userId: string): Promise<boolean> {
  const res = await axios.delete(`${BASE_URL}/users/delete`, {
    data: { user_id: userId },
  });
  return res.data.status === "ok";
}

/** Get all chats for a user (array of [chatId, chatTitle]) */
export async function getChatsForUser(
  userId: string
): Promise<[string, string][]> {
  const res = await axios.get<{ chats: [string, string][] }>(
    `${BASE_URL}/users/${userId}/chats`
  );
  return res.data.chats;
}

/** Get all messages for a chat */
export async function getMessagesForChat(
  userId: string,
  chatId: string
): Promise<
  { sender: "assistant" | "user" | "log"; text: string; time_stamp: number }[]
> {
  // time_stamp is in milliseconds
  const res = await axios.get<{
    messages: {
      sender: "assistant" | "user" | "log";
      text: string;
      time_stamp: number;
    }[];
  }>(`${BASE_URL}/chat/messages/${userId}/${chatId}`);
  return res.data.messages;
}

/** Create a new chat and return chatId */
export async function createChat(userId: string): Promise<string> {
  const res = await axios.post<{ chat_id: string }>(`${BASE_URL}/chat/create`, {
    user_id: userId,
  });
  return res.data.chat_id;
}

/** Rename a chat */
export async function renameChat(
  userId: string,
  chatId: string,
  newTitle: string
): Promise<boolean> {
  const res = await axios.post<{ status: string }>(`${BASE_URL}/chat/rename`, {
    user_id: userId,
    chat_id: chatId,
    new_title: newTitle,
  });
  return res.data.status === "ok";
}

/** Delete a chat */
export async function deleteChat(
  userId: string,
  chatId: string
): Promise<boolean> {
  const res = await axios.delete<{ status: string }>(
    `${BASE_URL}/chat/delete`,
    {
      data: { user_id: userId, chat_id: chatId }, // DELETE needs data in axios
    }
  );
  return res.data.status === "ok";
}
