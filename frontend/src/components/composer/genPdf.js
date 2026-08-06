import jsPDF from "jspdf";
import autoTable from  'jspdf-autotable';

// for the font
const getFontAsBinaryString = async (url) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch font: ${response.statusText}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  const binaryString = new Uint8Array(arrayBuffer).reduce(
    (data, byte) => data + String.fromCharCode(byte),
    ''
  );
  return binaryString;
};

//  for the logo
const getImageAsBase64 = async (url) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch image: ${response.statusText}`);
  }
  const blob = await response.blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

export const genPdf = async (items, patientInfo) => {
  try {
    const fontUrl = '/Poppins-Regular.ttf'; 
    const logoUrl = '/assets/mainlogo.png'; 

    const [poppinsFont, logo] = await Promise.all([
      getFontAsBinaryString(fontUrl),
      getImageAsBase64(logoUrl)
    ]);

    const doc = new jsPDF();

    doc.addFileToVFS('Poppins-Regular.ttf', poppinsFont);
    doc.addFont('Poppins-Regular.ttf', 'Poppins', 'normal');
    doc.setFont('Poppins'); 

    const logoWidth = 80;
    const logoHeight = 15; 
    const pageWidth = doc.internal.pageSize.getWidth();
    const logoX = pageWidth - logoWidth - 14; // Position on the top right
    const logoY = 15;
    doc.addImage(logo, 'PNG', logoX, logoY, logoWidth, logoHeight);

    doc.setFontSize(20);
    doc.text("Your Patient Codes", 14, 22);

    const hasPatientInfo = patientInfo.name || patientInfo.email || patientInfo.phone;
    let startY = 40;

    if (hasPatientInfo) {
      doc.setFontSize(12);
      doc.text("Patient Information", 14, startY);
      startY += 8;

      doc.setFontSize(10);
      if (patientInfo.name) {
        doc.text(`Name: ${patientInfo.name}`, 14, startY);
        startY += 7;
      }
      if (patientInfo.email) {
        doc.text(`Email: ${patientInfo.email}`, 14, startY);
        startY += 7;
      }
      if (patientInfo.phone) {
        doc.text(`Phone: ${patientInfo.phone}`, 14, startY);
        startY += 7;
      }
      startY += 5;
    }

    // Prepare data for the table
    const tableColumn = ["Name: Diacritical / Devnagari", "NAMASTE Code", "ICD-11 Code", "Description"];
    const tableRows = items.map(item => [
      item.display || item.title || 'N/A',
      item.nam_code || 'None',
      item.icd_code || 'None',
      item.long_definition || item.definition || 'No Description Available'
    ]);

    autoTable(doc, {
      head: [tableColumn],
      body: tableRows,
      startY: startY,
      theme: 'grid',
      headStyles: {
        fillColor: [41, 128, 185],
        textColor: 255,
        font: 'Poppins', 
        fontStyle: 'bold',
      },
      styles: {
        font: 'Poppins', 
        fontStyle: 'normal',
      },
      alternateRowStyles: {
        fillColor: [245, 245, 245],
      }
    });

    // footer with page numbers and generation date
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      const pageNumText = `Page ${i} of ${pageCount}`;
      const generatedDate = `Generated on: ${new Date().toLocaleDateString()}`;
      doc.setFontSize(8);
      doc.text(generatedDate, 14, doc.internal.pageSize.height - 10);
      doc.text(pageNumText, doc.internal.pageSize.width - 40, doc.internal.pageSize.height - 10);
    }

    const fileName = `medical-codes-${new Date().toISOString().split('T')[0]}.pdf`;
    doc.save(fileName);

  } catch (error) {
    console.error("Failed to generate PDF:", error);
    alert("Could not generate PDF. The required font file failed to load.");
  }
};