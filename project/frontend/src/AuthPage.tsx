import { useState } from "react";
import { useAuth } from "./AuthContext";
import { useNavigate } from "react-router-dom";

export default function AuthPage() {

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async () => {

    setError("");

    let res;

    if (isLogin) {
      res = await login(email, password);
      if (res.access_token) navigate("/home");
    } else {
      res = await register(email, password, username);
      if (res.message) {
        setIsLogin(true);
        setError("Account created. Please login.");
      }
    }

    if (res.error) setError(res.error);
  };

  return (
    <div className="auth-container">
      <div className="auth-box">

        <h1>{isLogin ? "Login" : "Create Account"}</h1>

        {!isLogin && (
          <input
            placeholder="Username"
            onChange={e => setUsername(e.target.value)}
          />
        )}

        <input
          placeholder="Email"
          onChange={e => setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          onChange={e => setPassword(e.target.value)}
        />

        {error && <p className="error">{error}</p>}

        <button onClick={handleSubmit}>
          {isLogin ? "Login" : "Register"}
        </button>

        <p onClick={() => setIsLogin(!isLogin)} className="switch">
          {isLogin ? "Create account" : "Back to login"}
        </p>

      </div>
    </div>
  );
}
