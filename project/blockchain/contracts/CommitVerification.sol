// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CommitVerification {
    struct Commit {
        string commitHash;
        uint256 riskScore;
        string status;
        address submitter;
        uint256 timestamp;
    }

    mapping(string => Commit) public commits;
    string[] public commitHashes;

    event CommitLogged(
        string indexed commitHash,
        uint256 riskScore,
        string status,
        address indexed submitter,
        uint256 timestamp
    );

    function logCommit(
        string memory _commitHash,
        uint256 _riskScore,
        string memory _status
    ) public {
        require(bytes(_commitHash).length > 0, "Commit hash cannot be empty");
        require(_riskScore <= 100, "Risk score must be between 0 and 100");

        Commit memory newCommit = Commit({
            commitHash: _commitHash,
            riskScore: _riskScore,
            status: _status,
            submitter: msg.sender,
            timestamp: block.timestamp
        });

        commits[_commitHash] = newCommit;
        commitHashes.push(_commitHash);

        emit CommitLogged(
            _commitHash,
            _riskScore,
            _status,
            msg.sender,
            block.timestamp
        );
    }

    function getCommit(string memory _commitHash)
        public
        view
        returns (
            string memory commitHash,
            uint256 riskScore,
            string memory status,
            address submitter,
            uint256 timestamp
        )
    {
        Commit memory commit = commits[_commitHash];
        return (
            commit.commitHash,
            commit.riskScore,
            commit.status,
            commit.submitter,
            commit.timestamp
        );
    }

    function getTotalCommits() public view returns (uint256) {
        return commitHashes.length;
    }

    function getCommitByIndex(uint256 index)
        public
        view
        returns (
            string memory commitHash,
            uint256 riskScore,
            string memory status,
            address submitter,
            uint256 timestamp
        )
    {
        require(index < commitHashes.length, "Index out of bounds");
        string memory hash = commitHashes[index];
        return getCommit(hash);
    }
}
