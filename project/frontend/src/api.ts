const API_URL = "http://localhost:5000/api";

export const getToken = () => {
  return localStorage.getItem("access_token");
};

export const login = async (email: string, password: string) => {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  });

  const data = await response.json();

  if (data.access_token) {
    localStorage.setItem("access_token", data.access_token);
  }

  return data;
};

export const register = async (
  email: string,
  password: string,
  username: string
) => {
  const response = await fetch(`${API_URL}/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password, username })
  });

  return response.json();
};

export const getLogs = async () => {
  const token = getToken();

  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_URL}/logs`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error("Unauthorized");
  }

  return response.json();
};
