import { Request, Response } from "express";
import cloudinary from "../utils/cloudinary";
import { LineItem } from "../models/LineItem";
import streamifier from "streamifier";

export const uploadLineItemImage = async (req: Request, res: Response) => {
  const { line_item_id, type } = req.params; // type: "before" or "after"
  if (!req.file) return res.status(400).json({ message: "No image file provided" });

  try {
    const stream = cloudinary.uploader.upload_stream(
      { resource_type: "image" },
      async (error, result) => {
        if (error || !result) {
          return res.status(500).json({ message: "Cloudinary upload failed", error });
        }

        // Update LineItem with image URL
        const updateField = type === "before" ? { before_img: result.secure_url } : { after_img: result.secure_url };
        const updated = await LineItem.findOneAndUpdate(
          { line_item_id },
          { $set: updateField },
          { new: true }
        );

        if (!updated) return res.status(404).json({ message: "LineItem not found" });
        res.status(200).json(updated);
      }
    );
    streamifier.createReadStream(req.file.buffer).pipe(stream);
  } catch (err) {
    res.status(500).json({ message: "Server error uploading image", error: err });
  }
};