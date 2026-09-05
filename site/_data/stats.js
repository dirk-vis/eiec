const records = require("./records.json");

module.exports = () => {
  const own = records.filter((r) => r.source !== "partner");
  const partner = records.filter((r) => r.source === "partner");
  const authors = new Set(records.map((r) => r.author));

  return {
    total: records.length,
    ownTotal: own.length,
    partnerTotal: partner.length,
    uniqueAuthors: authors.size,
  };
};
