import React,
{
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode
} from "react";


// USER TYPE
interface User {
  user_id: string;
  email: string;
  username: string;
}


// CONTEXT TYPE
interface AuthContextType {

  user: User | null;
  token: string | null;
  isInitialized: boolean;

  login: (email: string, password: string) => Promise<any>;
  logout: () => void;
}


// CREATE CONTEXT
const AuthContext = createContext<AuthContextType | undefined>(undefined);


// STORAGE KEYS
const TOKEN_KEY = "access_token";
const USER_KEY = "user_data";


// PROVIDER
export const AuthProvider = ({ children }: { children: ReactNode }) => {

  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);


  // LOAD FROM STORAGE ON START
  useEffect(() => {

    try {

      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedUser = localStorage.getItem(USER_KEY);

      if (savedToken && savedUser) {

        setToken(savedToken);
        setUser(JSON.parse(savedUser));

      }

    } catch (error) {

      console.error("Auth load error:", error);

      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);

    }

    setIsInitialized(true);

  }, []);



  // LOGIN FUNCTION
  const login = async (email: string, password: string) => {

    try {

      const response = await fetch("http://127.0.0.1:5000/login", {

        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          email,
          password
        })

      });


      const data = await response.json();


      if (data.access_token) {

        const userData = {

          user_id: data.user_id,
          email: data.email,
          username: data.username

        };


        setUser(userData);
        setToken(data.access_token);

        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));

      }

      return data;

    } catch (error) {

      console.error("Login error:", error);

      return {
        message: "Server error"
      };

    }

  };



  // LOGOUT FUNCTION
  const logout = () => {

    setUser(null);
    setToken(null);

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

  };



  return (

    <AuthContext.Provider
      value={{
        user,
        token,
        isInitialized,
        login,
        logout
      }}
    >

      {children}

    </AuthContext.Provider>

  );

};



// HOOK
export const useAuth = () => {

  const context = useContext(AuthContext);

  if (!context) {

    throw new Error(
      "useAuth must be used inside AuthProvider"
    );

  }

  return context;

};
