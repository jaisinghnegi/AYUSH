import * as XLSX from "xlsx";

export const genXlsx = (items, patientInfo) => {
  const worksheetData = [
    ...(patientInfo.name || patientInfo.email || patientInfo.phone ? [
      ['PATIENT INFORMATION'],
      ['Name', patientInfo.name || ''],
      ['Email', patientInfo.email || ''],
      ['Phone', patientInfo.phone || ''],
      [''], // Empty row for spacing
      ['MEDICAL CODES'],
    ] : [['MEDICAL CODES']]),
    // Header row for the medical codes
    ['Name: Diacritical / Devnagari', 'NAMASTE Code', 'ICD-11 Code', 'Description'],
    // Map over the items to create a row for each
    ...items.map(item => [
      item.display || item.title || '',
      item.nam_code || '',
      item.icd_code || '',
      item.long_definition || item.definition || 'No Description Available'
    ])
  ];

  const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);
  
  // Set custom column widths for better readability
  worksheet['!cols'] = [
    { width: 30 }, // Title/Display
    { width: 15 }, // ICD Code
    { width: 15 }, // NAM Code
    { width: 20 }, // Combined Code
    { width: 10 }  // ID
  ];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Medical Codes');

  // Create a second sheet for metadata
  const metadataSheet = XLSX.utils.aoa_to_sheet([
    ['FHIR Bundle Metadata'],
    ['Generated On', new Date().toISOString()],
    ['Total Items', items.length],
    ['Bundle Type', 'collection']
  ]);
  XLSX.utils.book_append_sheet(workbook, metadataSheet, 'Metadata');

  XLSX.writeFile(workbook, `fhir-bundle-${new Date().toISOString().split('T')[0]}.xlsx`);
};