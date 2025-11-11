import { Router } from "express";
import { 
  createAnnouncement, 
  getAllAnnouncements, 
  updateAnnouncement, 
  deleteAnnouncement 
} from "../controllers/announcementsController";

const router = Router();

// Create announcement
router.post("/", createAnnouncement);

// Get announcements by branch_id (query param)
router.get("/", getAllAnnouncements);

// Update announcement by ID (announcement_id in params)
router.put("/:id", updateAnnouncement);

// Delete announcement by ID (announcement_id in params)
router.delete("/:id", deleteAnnouncement);

export default router;
