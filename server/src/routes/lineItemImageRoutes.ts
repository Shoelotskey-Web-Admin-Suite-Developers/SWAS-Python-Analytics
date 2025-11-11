import { Router } from "express";
import multer from "multer";
import { uploadLineItemImage } from "../controllers/lineItemImageController";

const router = Router();
const upload = multer({ storage: multer.memoryStorage() });

router.post("/upload/:line_item_id/:type", upload.single("image"), uploadLineItemImage);

export default router;