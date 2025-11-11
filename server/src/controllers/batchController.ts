import { Request, Response } from "express";
import { LineItem } from "../models/LineItem";
import { Transaction } from "../models/Transactions";
import { Dates } from "../models/Dates";
import mongoose from "mongoose";

const CONFIRMATION_CODE = "CONFIRM_DELETE"; // You can set this to any value you want

/**
 * Delete all records from multiple tables
 */
export const deleteAllData = async (req: Request, res: Response) => {
  const { confirmationCode } = req.body;
  
  // Simple validation to prevent accidental deletion
  if (!confirmationCode || confirmationCode !== CONFIRMATION_CODE) {
    return res.status(400).json({
      success: false,
      message: "Invalid confirmation code. Data deletion aborted."
    });
  }
  
  const session = await mongoose.startSession();
  
  try {
    session.startTransaction();
    
    // Delete records from all tables
    const results = await Promise.all([
      LineItem.deleteMany({}).session(session),
      Transaction.deleteMany({}).session(session),
      Dates.deleteMany({}).session(session)
      // Add other models as needed
    ]);
    
    await session.commitTransaction();
    
    // Calculate total deleted records
    const totalDeleted = results.reduce((sum, result) => sum + result.deletedCount, 0);
    
    return res.status(200).json({ 
      success: true,
      message: `All data has been deleted successfully. ${totalDeleted} records were removed.`,
      deletedCount: totalDeleted
    });
  } catch (error) {
    await session.abortTransaction();
    console.error("Batch delete error:", error);
    
    return res.status(500).json({
      success: false,
      message: "Failed to delete data",
      error: error instanceof Error ? error.message : String(error)
    });
  } finally {
    session.endSession();
  }
};