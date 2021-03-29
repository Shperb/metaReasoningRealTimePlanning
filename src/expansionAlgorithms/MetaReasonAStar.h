#pragma once
#include "../utility/PriorityQueue.h"
#include "../utility/ResultContainer.h"
#include <functional>
#include <memory>
#include <unordered_map>

#include "../utility/debug.h"

using namespace std;

template<class Domain, class Node>
class MetaReasonAStar
{
    typedef typename Domain::State     State;
    typedef typename Domain::Cost      Cost;
    typedef typename Domain::HashState Hash;

public:
    MetaReasonAStar(Domain& domain_, size_t lookahead_, string sorting_)
        : domain(domain_)
        , lookahead(lookahead_)
        , sortingFunction(sorting_)
    {}

    void expand(
      PriorityQueue<shared_ptr<Node>>&              open,
      unordered_map<State, shared_ptr<Node>, Hash>& closed,
      std::function<bool(shared_ptr<Node>,
                         unordered_map<State, shared_ptr<Node>, Hash>&,
                         PriorityQueue<shared_ptr<Node>>&)>
                       duplicateDetection,
      ResultContainer& res)
    {
        // First things first, reorder open so it matches our expansion policy
        // needs
        sortOpen(open);

        // This starts at 1, because we had to expand start to get the top level
        // actions
        size_t expansions = 1;

        // Expand until the limit
        vector<string> visited;
        while (!open.empty() && (expansions < lookahead)) {
            // Pop lowest fhat-value off open
            shared_ptr<Node> cur = open.top();

            string debugStr = "";
            debugStr += "{g: " + to_string(cur->getGValue()) + ",";
            debugStr += "h: " + to_string(cur->getHValue()) + ",";
            debugStr += "f: " + to_string(cur->getFValue()) + ",";
            debugStr += "expansion: " + to_string(expansions) + "}";

            DEBUG_MSG(debugStr);

            visited.push_back(cur->getState().toString());
            // Check if current node is goal
            if (domain.isGoal(cur->getState())) {
                DEBUG_MSG("reach goal in expansion");
                res.visited.push_back(visited);
                return;
            }

            res.nodesExpanded++;
            res.GATnodesExpanded++;
            expansions++;

            open.pop();
            cur->close();

            vector<State> children = domain.successors(cur->getState());
            res.nodesGenerated += children.size();

            State bestChild;
            Cost  bestF = numeric_limits<double>::infinity();

            for (State child : children) {
                shared_ptr<Node> childNode = make_shared<Node>(
                  cur->getGValue() + domain.getEdgeCost(child),
                  domain.heuristic(child), domain.distance(child),
                  domain.distanceErr(child), cur->getPathBasedEpsilonH(),
                  cur->getPathBasedEpsilonD(),
                  cur->getPathBasedExpansionCounter(), child, cur);

                bool dup = duplicateDetection(childNode, closed, open);

                if (!dup && childNode->getFValue() < bestF) {
                    bestF     = childNode->getFValue();
                    bestChild = child;
                }

                // Duplicate detection
                if (!dup) {
                    open.push(childNode);
                    closed[child] = childNode;
                }
            }

            // Learn one-step error
            if (bestF != numeric_limits<double>::infinity()) {
                Cost epsD = (1 + domain.distance(bestChild)) - cur->getDValue();
                Cost epsH = (domain.getEdgeCost(bestChild) +
                             domain.heuristic(bestChild)) -
                            cur->getHValue();

                cur->pushPathBasedEpsilons(epsH, epsD);
            }
        }

        res.visited.push_back(visited);
    }

private:
    void sortOpen(PriorityQueue<shared_ptr<Node>>& open)
    {
        if (sortingFunction == "f")
            open.swapComparator(Node::compareNodesF);
        else if (sortingFunction == "fhat")
            open.swapComparator(Node::compareNodesFHat);
    }

protected:
    Domain& domain;
    size_t  lookahead;
    string  sortingFunction;
};
