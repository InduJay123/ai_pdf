import { useState } from "react";
import api from "../api/axios";

const Register:React.FC = () => {

    const [form, setForm] = useState({username:"", email: "", password:""});

    const handleSubmit = async (e) => {
        e.preventDefault();
        await api.post("/api/register/", form);
        alert("Registered!");
    };

    return(
        <form onSubmit={handleSubmit}>
            <input placeholder="username"
                onChange={(e) => setForm({...form, username: e.target.value})}/>
            <input placeholder="email"
                onChange={(e) => setForm({...form, email: e.target.value})}/>
            <input type="password" placeholder="password"
                onChange={(e) => setForm({...form, password: e.target.value})}/>
            <button type="submit"> Register </button>
        </form>
    );
}

export default Register;