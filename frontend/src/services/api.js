import axios from "axios";

const API = "http://localhost:5000";
const API_URL = import.meta.env.VITE_API_URL;

export const sendMessage = (message) =>
  axios.post(`${API_URL}/chat`, { message });

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append("file", file);

  return axios.post(`${API_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDocuments = () =>
  axios.get(`${API}/documents`);

export const deleteDocument = (filename) =>
  axios.delete(`${API}/documents/${filename}`);