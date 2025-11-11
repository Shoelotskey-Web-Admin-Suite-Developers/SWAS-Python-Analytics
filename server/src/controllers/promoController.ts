import { Request, Response } from "express";
import { Promo } from "../models/Promo";
import { format } from "date-fns";

// Helper: convert Date[] to grouped duration string
const generateDurationString = (dates: Date[]): string => {
  if (!dates.length) return "";
  const sorted = [...dates].sort((a, b) => a.getTime() - b.getTime());
  const groups: Date[][] = [];
  let currentGroup: Date[] = [sorted[0]];

  for (let i = 1; i < sorted.length; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];
    const diff = (curr.getTime() - prev.getTime()) / (1000 * 60 * 60 * 24);

    if (diff === 1) currentGroup.push(curr);
    else {
      groups.push(currentGroup);
      currentGroup = [curr];
    }
  }
  groups.push(currentGroup);

  return groups
    .map((g) =>
      g.length === 1
        ? format(g[0], "MMM d, yyyy")
        : `${format(g[0], "MMM d")}–${format(
            g[g.length - 1],
            g[0].getFullYear() !== g[g.length - 1].getFullYear() ? "MMM d, yyyy" : "d, yyyy"
          )}`
    )
    .join(", ");
};

// Create promo
export const createPromo = async (req: Request, res: Response) => {
  try {
    const { promo_title, promo_description, promo_dates, branch_id } = req.body;

    if (!promo_title || !promo_dates || !branch_id || !promo_dates.length) {
      return res.status(400).json({ error: "Title, dates, and branch_id are required" });
    }

    // Convert strings to Date objects
    const dateObjects = promo_dates.map((d: string) => new Date(d));

    // Generate unique promo_id
    const lastPromo = await Promo.findOne().sort({ _id: -1 });
    const nextIdNumber = lastPromo
      ? parseInt(lastPromo.promo_id.replace("PROMO-", ""), 10) + 1
      : 1;
    const promo_id = `PROMO-${nextIdNumber}`;

    const duration = generateDurationString(dateObjects);

    const promo = new Promo({
      promo_id,
      promo_title,
      promo_description: promo_description || null,
      promo_dates: dateObjects,
      promo_duration: duration,
      branch_id,
    });

    const savedPromo = await promo.save();

    return res.status(201).json({
      promo: {
        _id: savedPromo._id,
        promo_id: savedPromo.promo_id,
        promo_title: savedPromo.promo_title,
        promo_description: savedPromo.promo_description,
        promo_dates: savedPromo.promo_dates,
        promo_duration: savedPromo.promo_duration,
        branch_id: savedPromo.branch_id,
      },
    });
  } catch (err: any) {
    console.error("Error creating promo:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Get promos filtered by branch_id
export const getAllPromos = async (req: Request, res: Response) => {
  try {
    const { branch_id, all } = req.query;

    let filter: any = {};
    if (!all) {
      if (!branch_id) {
        return res.status(400).json({ error: "branch_id query is required" });
      }
      filter.branch_id = branch_id.toString();
    }

    const promos = await Promo.find(filter).sort({ _id: -1 });

    const formattedPromos = promos.map((p) => ({
      _id: p._id,
      promo_id: p.promo_id,
      promo_title: p.promo_title,
      promo_description: p.promo_description,
      promo_dates: p.promo_dates,
      promo_duration: p.promo_duration,
      branch_id: p.branch_id,
    }));

    return res.status(200).json({ promos: formattedPromos });
  } catch (err: any) {
    console.error("Error fetching promos:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Update promo
export const updatePromo = async (req: Request, res: Response) => {
  try {
    const { id } = req.params; // promo_id
    const { promo_title, promo_description, promo_dates } = req.body;

    if (!promo_title && !promo_description && !promo_dates) {
      return res.status(400).json({ error: "Nothing to update" });
    }

    let updateData: any = {};
    if (promo_title) updateData.promo_title = promo_title;
    if (promo_description !== undefined) updateData.promo_description = promo_description;
    if (promo_dates) {
      const dateObjects = promo_dates.map((d: string) => new Date(d));
      updateData.promo_dates = dateObjects;
      updateData.promo_duration = generateDurationString(dateObjects);
    }

    const updatedPromo = await Promo.findOneAndUpdate({ promo_id: id }, updateData, { new: true });

    if (!updatedPromo) {
      return res.status(404).json({ error: "Promo not found" });
    }

    return res.status(200).json({
      promo: {
        _id: updatedPromo._id,
        promo_id: updatedPromo.promo_id,
        promo_title: updatedPromo.promo_title,
        promo_description: updatedPromo.promo_description,
        promo_dates: updatedPromo.promo_dates,
        promo_duration: updatedPromo.promo_duration,
        branch_id: updatedPromo.branch_id,
      },
    });
  } catch (err: any) {
    console.error("Error updating promo:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};

// Delete promo
export const deletePromo = async (req: Request, res: Response) => {
  try {
    const { id } = req.params; // promo_id

    const deletedPromo = await Promo.findOneAndDelete({ promo_id: id });

    if (!deletedPromo) {
      return res.status(404).json({ error: "Promo not found" });
    }

    return res.status(200).json({
      message: "Promo deleted successfully",
      _id: deletedPromo._id,
      promo_id: deletedPromo.promo_id,
    });
  } catch (err: any) {
    console.error("Error deleting promo:", err);
    return res.status(500).json({ message: "Server error", error: err.message });
  }
};
