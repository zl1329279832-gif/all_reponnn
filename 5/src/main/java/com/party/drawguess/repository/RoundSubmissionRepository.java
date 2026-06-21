package com.party.drawguess.repository;

import com.party.drawguess.model.RoundSubmission;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RoundSubmissionRepository extends JpaRepository<RoundSubmission, Long> {
    List<RoundSubmission> findByRoundIdOrderBySubmittedAtAsc(Long roundId);
    List<RoundSubmission> findByGameIdOrderBySubmittedAtAsc(Long gameId);
    Optional<RoundSubmission> findByRoundIdAndPlayerIdAndSubmissionType(
            Long roundId, Long playerId, RoundSubmission.SubmissionType submissionType);
    boolean existsByRoundIdAndPlayerIdAndSubmissionType(
            Long roundId, Long playerId, RoundSubmission.SubmissionType submissionType);
}
