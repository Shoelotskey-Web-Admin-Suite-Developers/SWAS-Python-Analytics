import { Request, Response } from "express";
import { Announcement } from "../models/Announcements";

// Create announcement
export const createAnnouncement = async (req: Request, res: Response) => {
  try {
    const { announcement_title, announcement_description, branch_id } = req.body;

    if (!announcement_title || !branch_id) {
      return res.status(400).json({ error: "Title and branch_id are required" });
    }

    // Generate unique announcement_id
    const lastAnnouncement = await Announcement.findOne().sort({ announcement_date: -1 });
    const nextIdNumber = lastAnnouncement
      ? parseInt(lastAnnouncement.announcement_id.replace("ANN-", ""), 10) + 1
      : 1;
    const announcement_id = `ANN-${nextIdNumber}`;

    const announcement = new Announcement({
      announcement_id,
      announcement_title,
      announcement_description: announcement_description || null,
      branch_id,
    });

    const savedAnnouncement = await announcement.save();

    return res.status(201).json({
      announcement: {
        _id: savedAnnouncement._id, // ✅ include _id
        announcement_id: savedAnnouncement.announcement_id,
        announcement_title: savedAnnouncement.announcement_title,
        announcement_description: savedAnnouncement.announcement_description,
        announcement_date: savedAnnouncement.announcement_date,
        branch_id: savedAnnouncement.branch_id,
      },
    });
  } catch (err: any) {
    console.error("Error creating announcement:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Get announcements filtered by branch_id
export const getAllAnnouncements = async (req: Request, res: Response) => {
  try {
    const { branch_id, all } = req.query;

    let filter: any = {};

    if (!all) {
      if (!branch_id) {
        return res.status(400).json({ error: "branch_id query is required" });
      }
      filter.branch_id = branch_id.toString();
    }

    const announcements = await Announcement.find(filter).sort({ announcement_date: -1 });

    const formattedAnnouncements = announcements.map(a => ({
      _id: a._id, // ✅ include _id
      announcement_id: a.announcement_id,
      announcement_title: a.announcement_title,
      announcement_description: a.announcement_description,
      announcement_date: a.announcement_date,
      branch_id: a.branch_id,
    }));

    return res.status(200).json({ announcements: formattedAnnouncements });
  } catch (err: any) {
    console.error("Error fetching announcements:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Update announcement
export const updateAnnouncement = async (req: Request, res: Response) => {
  try {
    const { id } = req.params; // announcement_id
    const { announcement_title, announcement_description } = req.body;

    if (!announcement_title && !announcement_description) {
      return res.status(400).json({ error: "Nothing to update" });
    }

    const updatedAnnouncement = await Announcement.findOneAndUpdate(
      { announcement_id: id },
      { announcement_title, announcement_description },
      { new: true }
    );

    if (!updatedAnnouncement) {
      return res.status(404).json({ error: "Announcement not found" });
    }

    return res.status(200).json({
      announcement: {
        _id: updatedAnnouncement._id, // ✅ include _id
        announcement_id: updatedAnnouncement.announcement_id,
        announcement_title: updatedAnnouncement.announcement_title,
        announcement_description: updatedAnnouncement.announcement_description,
        announcement_date: updatedAnnouncement.announcement_date,
        branch_id: updatedAnnouncement.branch_id,
      },
    });
  } catch (err: any) {
    console.error("Error updating announcement:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Delete announcement
export const deleteAnnouncement = async (req: Request, res: Response) => {
  try {
    const { id } = req.params; // announcement_id

    const deletedAnnouncement = await Announcement.findOneAndDelete({ announcement_id: id });

    if (!deletedAnnouncement) {
      return res.status(404).json({ error: "Announcement not found" });
    }

    return res.status(200).json({
      message: "Announcement deleted successfully",
      _id: deletedAnnouncement._id, // ✅ include _id (in case frontend needs to remove it from state)
      announcement_id: deletedAnnouncement.announcement_id,
    });
  } catch (err: any) {
    console.error("Error deleting announcement:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};
