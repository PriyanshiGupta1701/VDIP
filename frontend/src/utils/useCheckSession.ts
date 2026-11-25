import { useEffect } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import getCookie from "@/utils/getCookie"
import { useUserContext } from "@/context/userContext"
import { toast } from "react-toastify"

interface User {
    is_admin?: boolean
    // Add other user properties if needed
}

const useCheckSession = () => {
    const navigate = useNavigate()
    const location = useLocation()

    const {user} = useUserContext()

    useEffect(() => {
        const token = getCookie("access_token")

        if (!token) {
            navigate("/login")
            return
        }

        const isAdmin = user?.is_admin === true

        if (location.pathname.includes("admin_options") && !isAdmin) {
            toast.error("Access denied. Admins only.")
            navigate("/user")
        }

        console.log("token:", token)
    }, [navigate, location.pathname])
}

export default useCheckSession

