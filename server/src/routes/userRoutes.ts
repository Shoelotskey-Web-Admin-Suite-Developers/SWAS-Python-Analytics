import { Router } from "express";
import { addUser, getUsers, deleteUser, editUser } from "../controllers/userController";

const router = Router();

router.post("/users", addUser);
router.get("/users", getUsers);
router.delete("/users/:user_id", deleteUser);
router.put("/users/:user_id", editUser); // <-- Edit user

export default router;
