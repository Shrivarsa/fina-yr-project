import { motion } from "framer-motion";
import { FaCode, FaBug, FaDownload, FaUserCircle, FaMoon, FaSun } from "react-icons/fa";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Home() {

  const navigate = useNavigate();
  const [dark, setDark] = useState(true);

  useEffect(() => {
    document.body.className = dark ? "dark-theme" : "light-theme";
  }, [dark]);

  return (
    <div className="home-container">

      {/* HEADER */}
      <header className="navbar">
        <div className="logo">🚀 SCIP AI</div>

        <div className="nav-actions">
          <button onClick={() => setDark(!dark)} className="theme-btn">
            {dark ? <FaSun /> : <FaMoon />}
          </button>

          <FaUserCircle className="profile-icon" />
        </div>
      </header>


      {/* HERO SECTION */}
      <motion.div
        className="hero"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
      >
        <h1>AI Powered Code Security Platform</h1>
        <p>Secure. Analyze. Deploy with Confidence.</p>
      </motion.div>


      {/* FEATURE CARDS */}
      <div className="features">

        <motion.div
          className="card"
          whileHover={{ scale: 1.08 }}
          onClick={() => navigate("/push")}
        >
          <FaCode size={40} />
          <h3>Push Code</h3>
          <p>Upload and analyze your commits instantly.</p>
        </motion.div>

        <motion.div
          className="card"
          whileHover={{ scale: 1.08 }}
          onClick={() => navigate("/test")}
        >
          <FaBug size={40} />
          <h3>Test Your Code</h3>
          <p>Run vulnerability detection and AI scanning.</p>
        </motion.div>

        <motion.div
          className="card"
          whileHover={{ scale: 1.08 }}
          onClick={() => navigate("/source")}
        >
          <FaDownload size={40} />
          <h3>Get Source Code</h3>
          <p>Download AI optimized secure source files.</p>
        </motion.div>

      </div>

    </div>
  );
}
