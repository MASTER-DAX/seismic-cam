const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");

const app = express();
const uploadDir = path.join(__dirname, "uploads");

if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => cb(null, Date.now() + ".jpg")
});

const upload = multer({ storage: storage });

app.set("view engine", "ejs");
app.use("/uploads", express.static(uploadDir));

app.get("/", (req, res) => {
  const files = fs.readdirSync(uploadDir).sort((a, b) => b.localeCompare(a));
  res.render("index", { files });
});

app.post("/upload", upload.single("image"), (req, res) => {
  res.status(200).send("Image received");
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(Server running on port ${PORT}));
