import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import { useState } from "react";

const Login:React.FC = () => {

    const [form, setForm] = useState({ username:"", password:""});
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();

        try{
            const res = await api.post("/api/login/", {
                username : form.username,
                password: form.password,
            });

            localStorage.setItem("access", res.data.access);
            localStorage.setItem("refresh", res.data.refresh);

        navigate("/dashboard");
        }catch(err){
            console.error(err);
        }  
};
    return(
        <form onSubmit={handleLogin} className="flex flex-col p-8 border border-blue-800 rounded-xl m-8">
            <input placeholder="Username"
                className="border rounded-lg p-2"
                onChange={(e) => setForm({...form, username: e.target.value})}/>
            <input type="password" placeholder="Password"
                className="border rounded-lg p-2 mt-2"
                onChange={(e) => setForm({...form, password: e.target.value})}/>
            <button type="submit"
                className="bg-blue-900 text-white mt-8 font-bold text-md"
            > Login </button>
        </form>
    )
}

export default Login;