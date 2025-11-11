// src/controllers/customerController.ts
import { Request, Response } from "express";
import { Customer } from "../models/Customer";

// Get all customers
export const getCustomers = async (req: Request, res: Response): Promise<void> => {
  try {
    const customers = await Customer.find();
    res.status(200).json(customers);
  } catch (error) {
    res.status(500).json({ message: "Error fetching customers", error });
  }
};

// Get computed customer summaries (balance, current services, status)
export const getCustomerSummaries = async (_req: Request, res: Response): Promise<void> => {
  try {
    const summaries = await Customer.aggregate([
      {
        $lookup: {
          from: "transactions",
          let: { customerId: "$cust_id" },
          pipeline: [
            {
              $match: {
                $expr: { $eq: ["$cust_id", "$$customerId"] },
              },
            },
            {
              $project: {
                balanceContribution: {
                  $let: {
                    vars: {
                      diff: {
                        $subtract: [
                          { $ifNull: ["$total_amount", 0] },
                          { $ifNull: ["$amount_paid", 0] },
                        ],
                      },
                    },
                    in: {
                      $cond: [{ $gt: ["$$diff", 0] }, "$$diff", 0],
                    },
                  },
                },
              },
            },
            {
              $group: {
                _id: null,
                totalBalance: { $sum: "$balanceContribution" },
              },
            },
          ],
          as: "transactionSummary",
        },
      },
      {
        $lookup: {
          from: "line_items",
          let: { customerId: "$cust_id" },
          pipeline: [
            {
              $match: {
                $expr: {
                  $and: [
                    { $eq: ["$cust_id", "$$customerId"] },
                    { $ne: ["$current_status", "Picked Up"] },
                  ],
                },
              },
            },
            {
              $count: "currentServiceCount",
            },
          ],
          as: "lineItemSummary",
        },
      },
      {
        $addFields: {
          balance: {
            $ifNull: [{ $arrayElemAt: ["$transactionSummary.totalBalance", 0] }, 0],
          },
          currentServiceCount: {
            $ifNull: [{ $arrayElemAt: ["$lineItemSummary.currentServiceCount", 0] }, 0],
          },
        },
      },
      {
        $addFields: {
          status: {
            $cond: [{ $gt: ["$currentServiceCount", 0] }, "Active", "Dormant"],
          },
        },
      },
      {
        $project: {
          _id: 0,
          cust_id: 1,
          cust_name: 1,
          cust_bdate: 1,
          cust_address: 1,
          cust_email: 1,
          cust_contact: 1,
          total_services: 1,
          total_expenditure: 1,
          balance: 1,
          currentServiceCount: 1,
          status: 1,
        },
      },
      {
        $sort: { cust_name: 1 },
      },
    ]);

    res.status(200).json(summaries);
  } catch (error) {
    console.error("Error computing customer summaries:", error);
    res.status(500).json({ message: "Error computing customer summaries", error });
  }
};

// Get customer by ID
export const getCustomerById = async (req: Request, res: Response): Promise<void> => {
  try {
    const { cust_id } = req.params;

    const customer = await Customer.findOne({ cust_id });

    if (!customer) {
      res.status(404).json({ message: "Customer not found" });
      return;
    }

    res.status(200).json(customer);
  } catch (error) {
    res.status(500).json({ message: "Error fetching customer", error });
  }
};

// Get customer by name and birthday
export const getCustomerByNameAndBdate = async (req: Request, res: Response): Promise<void> => {
  try {
    const { cust_name, cust_bdate } = req.query;

    if (!cust_name || !cust_bdate) {
      res.status(400).json({ message: "cust_name and cust_bdate are required" });
      return;
    }

    // Parse birthday string into a Date range
    const birthdate = new Date(cust_bdate as string);
    const startOfDay = new Date(birthdate);
    startOfDay.setUTCHours(0, 0, 0, 0);

    const endOfDay = new Date(birthdate);
    endOfDay.setUTCHours(23, 59, 59, 999);

    // Search by case-insensitive name + birthdate within day range
    const customer = await Customer.findOne({
      cust_name: { $regex: new RegExp(`^${cust_name}$`, "i") },
      cust_bdate: { $gte: startOfDay, $lte: endOfDay },
    });

    if (!customer) {
      res.status(404).json({ message: "Customer not found" });
      return;
    }

    res.status(200).json(customer);
  } catch (error) {
    res.status(500).json({ message: "Error fetching customer by name and birthday", error });
  }
};



// Delete customer by cust_id
export const deleteCustomer = async (req: Request, res: Response): Promise<void> => {
  try {
    const { cust_id } = req.params;

    const deleted = await Customer.findOneAndDelete({ cust_id });

    if (!deleted) {
      res.status(404).json({ message: "Customer not found" });
      return;
    }

    res.status(200).json({ message: "Customer deleted successfully" });
  } catch (error) {
    res.status(500).json({ message: "Error deleting customer", error });
  }
};

// Delete all customers
export const deleteAllCustomers = async (req: Request, res: Response): Promise<void> => {
  try {
    const result = await Customer.deleteMany({});
    res.status(200).json({ message: `${result.deletedCount} customers deleted successfully` });
  } catch (error) {
    res.status(500).json({ message: "Error deleting all customers", error });
  }
};


// Update customer by cust_id
export const updateCustomer = async (req: Request, res: Response): Promise<void> => {
  try {
    const { cust_id } = req.params;
    const updateData = req.body;

    const updated = await Customer.findOneAndUpdate(
      { cust_id },
      updateData,
      { new: true, runValidators: true } // return updated doc + validate schema
    );

    if (!updated) {
      res.status(404).json({ message: "Customer not found" });
      return;
    }

    res.status(200).json(updated);
  } catch (error) {
    res.status(500).json({ message: "Error updating customer", error });
  }
};
