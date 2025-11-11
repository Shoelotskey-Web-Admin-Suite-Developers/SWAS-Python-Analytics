import { Router } from "express";
import { getBranches, getBranchByBranchId } from "../controllers/branchController";

const router = Router();

router.get("/", getBranches);

// GET branch by branch_id
router.get("/:branchId", getBranchByBranchId);

export default router;
