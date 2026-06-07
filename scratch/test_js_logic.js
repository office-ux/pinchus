// scratch/test_js_logic.js
const items = [
  {
    id: 655,
    pdf_path: "C:\\pinchus\\Projects\\321654\\pdfs\\QCC_Mechanical___Plumbing___Fire_Drawings.pdf",
    page: 1,
    xref: 766,
    pdf_name: "QCC_Mechanical___Plumbing___Fire_Drawings.pdf",
    pdf_uuid: "uuid-123",
    fields: {
      "PRELIMINARY CFM": "100",
      "PRELIMINARY %": "10",
      "TYPE": "FCU",
      "SIZE": "10x10"
    }
  }
];

const dynamicFieldsSet = new Set();
items.forEach(item => {
    if (item.fields) Object.keys(item.fields).forEach(k => dynamicFieldsSet.add(k));
});

const fixedCols = ["UUID", "PDF Name", "PDF UUID", "PDF File", "Page"];
const dynamicCols = Array.from(dynamicFieldsSet).sort();
const allFieldsArr = fixedCols.concat(dynamicCols);

// Case 1: localStorage is empty (savedOrder = [])
let savedOrder1 = [];
let sortedFields1 = [];
savedOrder1.forEach(col => { if (allFieldsArr.includes(col)) sortedFields1.push(col); });
const remaining1 = allFieldsArr.filter(c => !sortedFields1.includes(c));
sortedFields1 = sortedFields1.concat(remaining1);

console.log("Case 1 (empty localStorage) sortedFields:", sortedFields1);

// Case 2: localStorage has some columns
let savedOrder2 = ["FINAL %", "FINAL CFM", "FINAL VEL", "K-factor", "PRELIMINARY %", "PRELIMINARY CFM", "PRELIMINARY VEL", "SIZE", "TYPE"];
let sortedFields2 = [];
savedOrder2.forEach(col => { if (allFieldsArr.includes(col)) sortedFields2.push(col); });
const remaining2 = allFieldsArr.filter(c => !sortedFields2.includes(c));
sortedFields2 = sortedFields2.concat(remaining2);

console.log("Case 2 (partial localStorage) sortedFields:", sortedFields2);
