import express from "express";
import { deleteAllData } from "../controllers/batchController";

const router = express.Router();

// Route to delete all data
router.delete("/delete-all", deleteAllData);

export default router;