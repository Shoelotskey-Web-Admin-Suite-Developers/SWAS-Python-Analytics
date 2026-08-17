import { Request, Response } from "express"
import { DailyRevenue } from "../models/DailyRevenue"
import { Forecast } from "../models/Forecast"
import { MonthlyRevenue } from "../models/MonthlyRevenue"
import { LineItem } from "../models/LineItem"
import { Service } from "../models/Service"
import { Transaction } from "../models/Transactions"
import { Branch } from "../models/Branch" // Import Branch model

// Helper function to get branch mapping from database (only type 'B')
const getBranchIdMap = async (): Promise<{ [key: string]: string }> => {
  try {
    // Only fetch branches with type 'B'
    const branches = await Branch.find({ type: 'B' }).sort({ branch_number: 1 }).lean()
    const branchMap: { [key: string]: string } = {}
    
    // Map index-based IDs (1,2,3...) to actual branch_ids
    branches.forEach((branch: any, index: number) => {
      // Use index + 1 as the frontend ID
      branchMap[String(index + 1)] = branch.branch_id
    })
    
    return branchMap
  } catch (error) {
    console.error("Error fetching branch map:", error)
    return {}
  }
}

// Helper function to get all branches with type 'B'
const getBranchesByType = async (type: string = 'B'): Promise<any[]> => {
  try {
    return await Branch.find({ type }).sort({ branch_number: 1 }).lean()
  } catch (error) {
    console.error(`Error fetching branches with type ${type}:`, error)
    return []
  }
}

// Helper function to resolve branch filters (only for type 'B')
const resolveBranchFilter = async (branchesParam: string | undefined): Promise<any> => {
  if (!branchesParam || typeof branchesParam !== 'string') {
    return {}
  }

  const branchArray = branchesParam.split(',').filter(b => b.trim())
  if (branchArray.length === 0) {
    return {}
  }

  // Get branch mapping from database (only type 'B')
  const branchIdMap = await getBranchIdMap()
  
  // If "total" is selected or no specific branches, don't filter
  if (branchArray.includes("total") || branchArray.includes("0")) {
    return {}
  }

  // Resolve frontend IDs to actual branch_ids
  const actualBranchIds = branchArray
    .map(b => branchIdMap[b])
    .filter(Boolean) // Remove undefined values

  if (actualBranchIds.length === 0) {
    return {}
  }

  return { branch_id: { $in: actualBranchIds } }
}

// Helper function to get branch selection options (only type 'B')
export const getBranchOptions = async (req: Request, res: Response) => {
  try {
    // Only fetch branches with type 'B'
    const branches = await Branch.find({ type: 'B' }).sort({ branch_number: 1 }).lean()
    
    const options = branches.map((branch: any, index: number) => ({
      id: String(index + 1), // Use sequential number as frontend ID
      label: branch.branch_name,
      value: branch.branch_id,
      code: branch.branch_code,
      type: branch.type,
      branchNumber: branch.branch_number
    }))

    // Add "All Branches" option
    const allOption = {
      id: "0",
      label: "All Branches",
      value: "all",
      code: "ALL",
      type: "ALL",
      branchNumber: 0
    }

    return res.status(200).json([allOption, ...options])
  } catch (error) {
    console.error("Error fetching branch options:", error)
    return res.status(500).json({ error: "Failed to fetch branch options" })
  }
}

export const getDailyRevenue = async (req: Request, res: Response) => {
  try {
    // Return all daily revenue records sorted by date ascending
    const records = await DailyRevenue.find().sort({ date: 1 }).lean()
    return res.status(200).json(records)
  } catch (err) {
    console.error("Error fetching daily revenue:", err)
    return res.status(500).json({ error: "Failed to fetch daily revenue" })
  }
}

export const getForecast = async (req: Request, res: Response) => {
  try {
    // Fetch all forecast records sorted by date ascending
    const records = await Forecast.find().sort({ date: 1 }).lean()
    if (!records || records.length === 0) {
      return res.status(200).json([])
    }

    // Transform each record to a normalized dynamic shape:
    // { date: 'yyyy-MM-dd', total: number, branches: { [branch_id]: value } }
    const transformed = records.map((r: any) => {
      const dateStr = new Date(r.date).toISOString().slice(0,10)
      const branchEntries: Record<string, number> = {}

      // If record already has a branches object/map structure, copy numeric values
      if (r.branches && typeof r.branches === 'object') {
        if (Array.isArray(r.branches)) {
          r.branches.forEach((el: any) => {
            if (!el || typeof el !== 'object') return
            const id = el.branch_id || el.code || el.id || el.branch || el.name
            const val = el.value ?? el.amount ?? el.total ?? el.revenue
            if (id && typeof val === 'number') branchEntries[id] = val || 0
          })
        } else {
          Object.entries(r.branches).forEach(([bk, bv]) => {
            if (typeof bv === 'number') branchEntries[bk] = (bv as number) || 0
          })
        }
      }

      // Also scan top-level keys that look like branch identifiers (contain '-') with numeric values
      Object.keys(r).forEach(k => {
        if (k === 'date' || k === '_id' || k === '__v' || k === 'createdAt' || k === 'updatedAt' || k === 'branches' || k === 'total') return
        if (k.includes('-') && typeof r[k] === 'number') {
          if (branchEntries[k] == null) branchEntries[k] = r[k] || 0
        }
      })

      const total = typeof r.total === 'number'
        ? r.total
        : Object.values(branchEntries).reduce((s,v)=> s + (v||0), 0)

      return { date: dateStr, total, branches: branchEntries }
    })

    return res.status(200).json(transformed)
  } catch (err) {
    console.error("Error fetching forecast:", err)
    return res.status(500).json({ error: "Failed to fetch forecast" })
  }
}

export const getMonthlyRevenue = async (req: Request, res: Response) => {
  try {
    const records = await MonthlyRevenue.find().sort({ Year: 1 }).lean();
    if (records.length === 0) return res.status(200).json([]);

    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    const transformed = records.map((record: any) => {
      const monthIndex = monthNames.indexOf(record.month);
      const monthNumber = monthIndex !== -1 ? monthIndex + 1 : 1;
      const monthStr = `${record.Year}-${String(monthNumber).padStart(2,'0')}`;
      // Dynamically collect branch fields: heuristic - keys containing '-' and number value, excluding known meta keys.
      const branchEntries: Record<string, number> = {};
      Object.keys(record).forEach(k => {
        if (k === 'total' || k === 'month' || k === 'Year' || k === '_id' || k === '__v') return;
        if (k.includes('-') && typeof record[k] === 'number') {
          branchEntries[k] = record[k] || 0;
        }
      });
      // Fallback: some records may store a Map-like 'branches'
      if (record.branches && typeof record.branches === 'object') {
        Object.entries(record.branches).forEach(([bk, bv]) => {
          if (typeof bv === 'number') branchEntries[bk] = (bv as number) || 0;
        });
      }
      const total = typeof record.total === 'number' ? record.total : Object.values(branchEntries).reduce((s,v)=> s + (v||0), 0);
      return {
        month: monthStr,
        total,
        branches: branchEntries,
        sortKey: record.Year * 100 + monthNumber
      };
    }).sort((a,b)=> a.sortKey - b.sortKey).map(({sortKey, ...rest}) => rest);

    return res.status(200).json(transformed);
  } catch (err) {
    console.error('Error fetching monthly revenue (dynamic):', err);
    return res.status(500).json({ error: 'Failed to fetch monthly revenue' });
  }
};

export const getTopServices = async (req: Request, res: Response) => {
  try {
    // Get branch filter from query params
    const { branches } = req.query
    const branchFilter = await resolveBranchFilter(branches as string | undefined)
    
    // Get line items with branch filtering
    const lineItems = await LineItem.find(branchFilter).lean()
    
    // Count occurrences of each service
    const serviceCounts: { [key: string]: number } = {}
    
    lineItems.forEach((lineItem: any) => {
      if (lineItem.services && Array.isArray(lineItem.services)) {
        lineItem.services.forEach((service: any) => {
          const serviceId = service.service_id
          serviceCounts[serviceId] = (serviceCounts[serviceId] || 0) + (service.quantity || 1)
        })
      }
    })
    
    // Get service details for SERVICE-1, SERVICE-2, SERVICE-3, SERVICE-8, SERVICE-9
    const targetServices = ["SERVICE-1", "SERVICE-2", "SERVICE-3", "SERVICE-8", "SERVICE-9"]
    const services = await Service.find({
      service_id: { $in: targetServices }
    }).lean()
    
    // Create service name mapping
    const serviceNameMap: { [key: string]: string } = {}
    services.forEach((service: any) => {
      serviceNameMap[service.service_id] = service.service_name
    })
    
    // Build response data for individual services
    const individualServices = ["SERVICE-1", "SERVICE-2", "SERVICE-3"].map((serviceId) => ({
      service: serviceNameMap[serviceId] || serviceId,
      serviceId: serviceId,
      transactions: serviceCounts[serviceId] || 0,
      fill: getServiceColor(serviceId)
    }))
    
    // Combine SERVICE-8 and SERVICE-9 as "Color Renewal"
    const colorRenewalCount = (serviceCounts["SERVICE-8"] || 0) + (serviceCounts["SERVICE-9"] || 0)
    const colorRenewalService = {
      service: "Color Renewal",
      serviceId: "COLOR-RENEWAL",
      transactions: colorRenewalCount,
      fill: getServiceColor("COLOR-RENEWAL")
    }
    
    // Calculate date range from line items (using latest_update field)
    let earliestDate: Date | null = null
    let latestDate: Date | null = null
    
    lineItems.forEach((lineItem: any) => {
      const updateDate = new Date(lineItem.latest_update)
      if (!earliestDate || updateDate < earliestDate) {
        earliestDate = updateDate
      }
      if (!latestDate || updateDate > latestDate) {
        latestDate = updateDate
      }
    })
    
    // Combine all services
    const topServicesData = [...individualServices, colorRenewalService]
    
    // Include date range in response
    const response = {
      data: topServicesData,
      dateRange: {
        earliest: earliestDate,
        latest: latestDate,
        totalLineItems: lineItems.length
      }
    }
    
    return res.status(200).json(response)
  } catch (err) {
    console.error("Error fetching top services:", err)
    return res.status(500).json({ error: "Failed to fetch top services" })
  }
}

export const getSalesBreakdown = async (req: Request, res: Response) => {
  try {
    // Get branch filter from query params
    const { branches } = req.query
    const branchFilter = await resolveBranchFilter(branches as string | undefined)
    
    // Get all transactions with branch filtering
    const transactions = await Transaction.find(branchFilter).lean()
    
    // Calculate counts and amounts by payment status
    const statusData = {
      "NP": { count: 0, amount: 0 },
      "PARTIAL": { count: 0, amount: 0 },
      "PAID": { count: 0, amount: 0 }
    }
    
    transactions.forEach((transaction: any) => {
      const status = transaction.payment_status as keyof typeof statusData
      if (status in statusData) {
        statusData[status].count++
        
        // Calculate amount based on payment status
        const totalAmount = Number(transaction.total_amount || 0)
        const amountPaid = Number(transaction.amount_paid || 0)
        
        if (status === "PAID") {
          // For paid transactions, use total amount
          statusData[status].amount += totalAmount
        } else if (status === "PARTIAL") {
          // For partial transactions, use amount paid
          statusData[status].amount += amountPaid
        } else if (status === "NP") {
          // For unpaid transactions, use total amount (what's owed)
          statusData[status].amount += totalAmount
        }
      }
    })
    
    // Calculate date range from transactions
    let earliestDate: Date | null = null
    let latestDate: Date | null = null
    
    transactions.forEach((transaction: any) => {
      const dateIn = new Date(transaction.date_in)
      if (!earliestDate || dateIn < earliestDate) {
        earliestDate = dateIn
      }
      if (!latestDate || dateIn > latestDate) {
        latestDate = dateIn
      }
    })
    
    // Build response data
    const salesBreakdownData = [
      {
        status: "Unpaid",
        transactions: statusData.NP.count,
        amount: statusData.NP.amount,
        fill: "#DC2626"
      },
      {
        status: "Partially Paid", 
        transactions: statusData.PARTIAL.count,
        amount: statusData.PARTIAL.amount,
        fill: "#2563EB"
      },
      {
        status: "Paid",
        transactions: statusData.PAID.count,
        amount: statusData.PAID.amount,
        fill: "#16A34A"
      }
    ]
    
    // Include date range in response
    const response = {
      data: salesBreakdownData,
      dateRange: {
        earliest: earliestDate,
        latest: latestDate,
        totalTransactions: transactions.length
      }
    }
    
    return res.status(200).json(response)
  } catch (err) {
    console.error("Error fetching sales breakdown:", err)
    return res.status(500).json({ error: "Failed to fetch sales breakdown" })
  }
}

// Helper function to assign colors to services
function getServiceColor(serviceId: string): string {
  const colorMap: { [key: string]: string } = {
    "SERVICE-1": "#2563EB",    // blue
    "SERVICE-2": "#16A34A",    // green
    "SERVICE-3": "#F59E0B",    // amber
    "COLOR-RENEWAL": "#7C3AED"  // violet
  }
  return colorMap[serviceId] || "#6366F1" // fallback indigo
}