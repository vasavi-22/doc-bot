import axios from "axios";

const API = "http://localhost:5000";

export const sendMessage = (message) =>
  axios.post(`${API}/chat`, { message });

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append("file", file);

  return axios.post(`${API}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDocuments = () =>
  axios.get(`${API}/documents`);

export const deleteDocument = (filename) =>
  axios.delete(`${API}/documents/${filename}`);