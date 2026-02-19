const hre = require("hardhat");

async function main() {
  const CommitVerification = await hre.ethers.getContractFactory("CommitVerification");
  const contract = await CommitVerification.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();

  console.log("CommitVerification deployed to:", address);
  console.log("\nAdd to your backend/.env:");
  console.log(`WEB3_CONTRACT_ADDRESS=${address}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
