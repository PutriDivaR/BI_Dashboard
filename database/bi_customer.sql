-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jun 09, 2026 at 10:14 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.5.5

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `bi_customer`
--

-- --------------------------------------------------------

--
-- Table structure for table `dim_contract`
--

CREATE TABLE `dim_contract` (
  `contract_id` int(11) NOT NULL,
  `contract` varchar(50) DEFAULT NULL,
  `contractRiskLevel` varchar(10) DEFAULT NULL,
  `paperlessBilling` varchar(5) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `dim_customer`
--

CREATE TABLE `dim_customer` (
  `customer_id` int(11) NOT NULL,
  `customer` varchar(20) DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `seniorCitizen` varchar(15) DEFAULT NULL,
  `partner` varchar(5) DEFAULT NULL,
  `dependents` varchar(5) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `dim_payment`
--

CREATE TABLE `dim_payment` (
  `payment_id` int(11) NOT NULL,
  `paymentMethod` varchar(40) DEFAULT NULL,
  `paymentCategory` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `dim_services`
--

CREATE TABLE `dim_services` (
  `service_id` int(11) NOT NULL,
  `phoneService` varchar(10) DEFAULT NULL,
  `multipleLines` varchar(30) DEFAULT NULL,
  `internetService` varchar(30) DEFAULT NULL,
  `onlineSecurity` varchar(30) DEFAULT NULL,
  `onlineBackup` varchar(30) DEFAULT NULL,
  `deviceProtection` varchar(30) DEFAULT NULL,
  `techSupport` varchar(30) DEFAULT NULL,
  `streamingTV` varchar(30) DEFAULT NULL,
  `streamingMovies` varchar(30) DEFAULT NULL,
  `serviceCount` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `dim_tenure`
--

CREATE TABLE `dim_tenure` (
  `tenure_id` int(11) NOT NULL,
  `tenure` int(11) DEFAULT NULL,
  `tenureBucket` varchar(20) DEFAULT NULL,
  `tenureCategory` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `fact_churn`
--

CREATE TABLE `fact_churn` (
  `fact_id` int(11) NOT NULL,
  `customer_id` int(11) DEFAULT NULL,
  `contract_id` int(11) DEFAULT NULL,
  `payment_id` int(11) DEFAULT NULL,
  `service_id` int(11) DEFAULT NULL,
  `tenure_id` int(11) DEFAULT NULL,
  `churnFlag` int(11) DEFAULT NULL,
  `monthlyCharges` decimal(10,2) DEFAULT NULL,
  `totalCharges` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `dim_contract`
--
ALTER TABLE `dim_contract`
  ADD PRIMARY KEY (`contract_id`);

--
-- Indexes for table `dim_customer`
--
ALTER TABLE `dim_customer`
  ADD PRIMARY KEY (`customer_id`);

--
-- Indexes for table `dim_payment`
--
ALTER TABLE `dim_payment`
  ADD PRIMARY KEY (`payment_id`);

--
-- Indexes for table `dim_services`
--
ALTER TABLE `dim_services`
  ADD PRIMARY KEY (`service_id`);

--
-- Indexes for table `dim_tenure`
--
ALTER TABLE `dim_tenure`
  ADD PRIMARY KEY (`tenure_id`);

--
-- Indexes for table `fact_churn`
--
ALTER TABLE `fact_churn`
  ADD PRIMARY KEY (`fact_id`),
  ADD KEY `customer_id` (`customer_id`),
  ADD KEY `contract_id` (`contract_id`),
  ADD KEY `payment_id` (`payment_id`),
  ADD KEY `service_id` (`service_id`),
  ADD KEY `tenure_id` (`tenure_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `dim_contract`
--
ALTER TABLE `dim_contract`
  MODIFY `contract_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `dim_customer`
--
ALTER TABLE `dim_customer`
  MODIFY `customer_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `dim_payment`
--
ALTER TABLE `dim_payment`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `dim_services`
--
ALTER TABLE `dim_services`
  MODIFY `service_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `dim_tenure`
--
ALTER TABLE `dim_tenure`
  MODIFY `tenure_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `fact_churn`
--
ALTER TABLE `fact_churn`
  MODIFY `fact_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `fact_churn`
--
ALTER TABLE `fact_churn`
  ADD CONSTRAINT `fact_churn_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `dim_customer` (`customer_id`),
  ADD CONSTRAINT `fact_churn_ibfk_2` FOREIGN KEY (`contract_id`) REFERENCES `dim_contract` (`contract_id`),
  ADD CONSTRAINT `fact_churn_ibfk_3` FOREIGN KEY (`payment_id`) REFERENCES `dim_payment` (`payment_id`),
  ADD CONSTRAINT `fact_churn_ibfk_4` FOREIGN KEY (`service_id`) REFERENCES `dim_services` (`service_id`),
  ADD CONSTRAINT `fact_churn_ibfk_5` FOREIGN KEY (`tenure_id`) REFERENCES `dim_tenure` (`tenure_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
