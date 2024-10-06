//VERSION=3
function setup() {
  return {
    input: ["VV", "VH", "dataMask"],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  // Convert VV and VH bands to dB scale
  let vv_dB = 10 * Math.log10(sample.VV + 0.00001);
  let vh_dB = 10 * Math.log10(sample.VH + 0.00001);

  // Define the backscatter thresholds
  let waterThreshold = -20.0;
  let vhUrbanThreshold = -15.0; // Threshold to exclude urban areas

  // Fuzzy membership function for water likelihood
  let fuzzyMembership = 1 / (1 + Math.exp(-(vv_dB - waterThreshold) / 5));

  // Final flood classification based on fuzzy membership and VH filtering
  let isFlooded = vv_dB < waterThreshold && fuzzyMembership >= 0.4 && vh_dB < vhUrbanThreshold;

  // Return only blue for flood, transparent for non-flood
  return isFlooded ? [0.0, 0.0, 1.0, sample.dataMask] : [0.0, 0.0, 0.0, 0.0];
}