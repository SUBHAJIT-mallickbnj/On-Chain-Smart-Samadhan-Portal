// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ComplaintContract {
    struct Complaint {
        address user;
        string complaintHash;
        string department;
        string status;
        uint256 timestamp;
        bool exists;
    }
    
    mapping(string => Complaint) public complaints;
    mapping(address => string[]) public userComplaints;
    address public owner;
    
    event ComplaintSubmitted(
        string indexed referenceNo,
        address indexed user,
        string department,
        uint256 timestamp
    );
    
    event ComplaintStatusUpdated(
        string indexed referenceNo,
        string newStatus,
        uint256 timestamp
    );
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only contract owner can call this function");
        _;
    }
    
    function submitComplaint(
        string memory referenceNo,
        string memory complaintHash,
        string memory department,
        string memory status
    ) public {
        require(!complaints[referenceNo].exists, "Complaint already exists");
        
        complaints[referenceNo] = Complaint({
            user: msg.sender,
            complaintHash: complaintHash,
            department: department,
            status: status,
            timestamp: block.timestamp,
            exists: true
        });
        
        userComplaints[msg.sender].push(referenceNo);
        
        emit ComplaintSubmitted(referenceNo, msg.sender, department, block.timestamp);
    }
    
    function submitComplaintForUser(
        string memory referenceNo,
        string memory complaintHash,
        string memory department,
        string memory status,
        address userAddress
    ) public onlyOwner {
        require(!complaints[referenceNo].exists, "Complaint already exists");
        
        complaints[referenceNo] = Complaint({
            user: userAddress,
            complaintHash: complaintHash,
            department: department,
            status: status,
            timestamp: block.timestamp,
            exists: true
        });
        
        userComplaints[userAddress].push(referenceNo);
        
        emit ComplaintSubmitted(referenceNo, userAddress, department, block.timestamp);
    }
    
    function updateComplaintStatus(
        string memory referenceNo,
        string memory newStatus
    ) public onlyOwner {
        require(complaints[referenceNo].exists, "Complaint does not exist");
        
        complaints[referenceNo].status = newStatus;
        
        emit ComplaintStatusUpdated(referenceNo, newStatus, block.timestamp);
    }
    
    function getComplaint(string memory referenceNo)
        public
        view
        returns (
            address user,
            string memory complaintHash,
            string memory department,
            string memory status,
            uint256 timestamp
        )
    {
        require(complaints[referenceNo].exists, "Complaint does not exist");
        
        Complaint memory complaint = complaints[referenceNo];
        return (
            complaint.user,
            complaint.complaintHash,
            complaint.department,
            complaint.status,
            complaint.timestamp
        );
    }
    
    function getUserComplaints(address user)
        public
        view
        returns (string[] memory)
    {
        return userComplaints[user];
    }
    
    function verifyComplaintOwnership(string memory referenceNo, address user)
        public
        view
        returns (bool)
    {
        return complaints[referenceNo].exists && complaints[referenceNo].user == user;
    }
    
    function getAllComplaintsCount() public view returns (uint256) {
        // Note: This is a simple implementation. For production, you'd want a more efficient way
        return 0; // Placeholder - implement if needed
    }
}