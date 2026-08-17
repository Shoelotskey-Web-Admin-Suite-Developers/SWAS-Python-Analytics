// src/routes/branchRoutes.ts
import { Router } from "express";
import { 
  getBranches, 
  getBranchByBranchId, 
  createBranch,
  updateBranch,
  deleteBranch
} from "../controllers/branchController";

const router = Router();

// Get all branches
router.get("/", getBranches);

// Get branch by branch_id
router.get("/:branchId", getBranchByBranchId);

// Create a new branch
router.post("/", createBranch);

// Update a branch
router.put("/:branchId", updateBranch);

// Delete a branch
router.delete("/:branchId", deleteBranch);

export default router;