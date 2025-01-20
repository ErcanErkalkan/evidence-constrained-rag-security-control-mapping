import java.util.List;

public interface RankedVotingElection {
  /*
   * 
   * requires Set.copyOf(candidates).size() == candidates.size();
   * requires (\forall int i, j; i >= 0 && i < j && j < candidates.size();
   * !candidates.get(i).equals(candidates.get(j)));
   * requires (\forall int i, j; i >= 0 && i < candidates.size() && j >= 0 && j <
   * candidates.size(); i != j ==> !candidates.get(i).equals(candidates.get(j)));
   * 
   * @param candicates
   * 
   * @return true if the ballot was valid, false if invalid
   */

  boolean castVote(List<String> ballot);

  /*
   * @return the winner of the election, or null if no ballots were cast
   */
  String getWinner();

}
