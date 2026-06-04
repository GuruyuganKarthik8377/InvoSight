import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const extractInvoice = async (rawText, confidence) => {
  const res = await API.post("/extract", {
    raw_text: rawText,
    confidence: confidence,
  });
  return res.data;
};

export const extractInvoiceFile = async (file) => {
  const form = new FormData();
  form.append("file", file);
  const res = await API.post("/extract/file", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export default API;
