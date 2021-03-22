#pragma once
//#include "decisionAlgorithms/DecisionAlgorithm.h"
#include "decisionAlgorithms/MetaReasonScalarBackup.h"
#include "expansionAlgorithms/MetaReasonAStar.h"
#include "learningAlgorithms/MetaReasonDijkstra.h"
#include "utility/DiscreteDistribution.h"
#include "utility/PriorityQueue.h"
#include "utility/ResultContainer.h"
#include <functional>
#include <memory>
#include <set>
#include <unordered_map>
#include <vector>

#include <cassert>
#include <ctime>

#include "utility/debug.h"

using namespace std;

template<class Domain>
class RealTimeSearch
{
public:
    typedef typename Domain::State     State;
    typedef typename Domain::Cost      Cost;
    typedef typename Domain::HashState Hash;

    struct Node
    {
        Cost                 g;
        Cost                 h;
        Cost                 d;
        Cost                 derr;
        Cost                 epsH;
        Cost                 epsD;
        shared_ptr<Node>     parent;
        State                stateRep;
        bool                 open;
        int                  delayCntr;
        DiscreteDistribution distribution;

        shared_ptr<Node> nancyFrontier;
        Cost             backupHHat;

    public:
        Cost getGValue() const { return g; }
        Cost getHValue() const { return h; }
        Cost getDValue() const { return d; }
        Cost getDErrValue() const { return derr; }
        Cost getFValue() const { return g + h; }
        Cost getEpsilonH() const { return epsH; }
        Cost getEpsilonD() const { return epsD; }
        Cost getFHatValue() const { return g + getHHatValue(); }
        Cost getDHatValue() const { return (derr / (1.0 - epsD)); }
        Cost getHHatValue() const { return h + getDHatValue() * epsH; }

        State            getState() const { return stateRep; }
        shared_ptr<Node> getParent() const { return parent; }

        void setHValue(Cost val) { h = val; }
        void setGValue(Cost val) { g = val; }
        void setDValue(Cost val) { d = val; }
        void setDErrValue(Cost val) { derr = val; }
        void setEpsilonH(Cost val) { epsH = val; }
        void setEpsilonD(Cost val) { epsD = val; }
        void setState(State s) { stateRep = s; }
        void setParent(shared_ptr<Node> p) { parent = p; }

        bool onOpen() { return open; }
        void close() { open = false; }
        void reOpen() { open = true; }

        void markStart() { stateRep.markStart(); }

        void incDelayCntr() { delayCntr++; }
        int  getDelayCntr() { return delayCntr; }

        Node(Cost g_, Cost h_, Cost d_, Cost derr_, Cost epsH_, Cost epsD_,
             State state_, shared_ptr<Node> parent_)
            : g(g_)
            , h(h_)
            , d(d_)
            , derr(derr_)
            , epsH(epsH_)
            , epsD(epsD_)
            , parent(parent_)
            , stateRep(state_)
        {
            open      = true;
            delayCntr = 0;
        }

        friend std::ostream& operator<<(std::ostream& stream, const Node& node)
        {
            stream << node.getState() << endl;
            stream << "f: " << node.getFValue() << endl;
            stream << "g: " << node.getGValue() << endl;
            stream << "h: " << node.getHValue() << endl;
            stream << "derr: " << node.getDErrValue() << endl;
            stream << "d: " << node.getDValue() << endl;
            stream << "epsilon-h: " << node.getEpsilonH() << endl;
            stream << "epsilon-d: " << node.getEpsilonD() << endl;
            stream << "f-hat: " << node.getFHatValue() << endl;
            stream << "d-hat: " << node.getDHatValue() << endl;
            stream << "h-hat: " << node.getHHatValue() << endl;
            stream << "action generated by: " << node.getState().getLabel()
                   << endl;
            stream << "-----------------------------------------------" << endl;
            stream << endl;
            return stream;
        }

        static bool compareNodesF(const shared_ptr<Node> n1,
                                  const shared_ptr<Node> n2)
        {
            // Tie break on g-value
            if (n1->getFValue() == n2->getFValue()) {
                return n1->getGValue() > n2->getGValue();
            }
            return n1->getFValue() < n2->getFValue();
        }

        static bool compareNodesFHat(const shared_ptr<Node> n1,
                                     const shared_ptr<Node> n2)
        {
            // Tie break on g-value
            if (n1->getFHatValue() == n2->getFHatValue()) {
                if (n1->getFValue() == n2->getFValue()) {
                    if (n1->getGValue() == n2->getGValue()) {
                        return n1->getState().key() > n2->getState().key();
                    }
                    return n1->getGValue() > n2->getGValue();
                }
                return n1->getFValue() < n2->getFValue();
            }
            return n1->getFHatValue() < n2->getFHatValue();
        }

        static bool compareNodesFHatFromDist(const shared_ptr<Node> n1,
                                             const shared_ptr<Node> n2)
        {
            // Tie break on f-value then g-value
            if (n1->getFHatValueFromDist() == n2->getFHatValueFromDist()) {
                if (n1->getFValue() == n2->getFValue()) {
                    if (n1->getGValue() == n2->getGValue()) {
                        return n1->getState().key() > n2->getState().key();
                    }
                    return n1->getGValue() > n2->getGValue();
                }
                return n1->getFValue() < n2->getFValue();
            }
            return n1->getFHatValueFromDist() < n2->getFHatValueFromDist();
        }

        static bool compareNodesH(const shared_ptr<Node> n1,
                                  const shared_ptr<Node> n2)
        {
            if (n1->getHValue() == n2->getHValue()) {
                return n1->getGValue() > n2->getGValue();
            }
            return n1->getHValue() < n2->getHValue();
        }

        static bool compareNodesHHat(const shared_ptr<Node> n1,
                                     const shared_ptr<Node> n2)
        {
            if (n1->getHHatValue() == n2->getHHatValue()) {
                return n1->getGValue() > n2->getGValue();
            }
            return n1->getHHatValue() < n2->getHHatValue();
        }

        static bool compareNodesBackedHHat(const shared_ptr<Node> n1,
                                           const shared_ptr<Node> n2)
        {
            /*if (n1->backupHHat == n2->backupHHat) {*/
            // return n1->getGValue() > n2->getGValue();
            /*}*/
            return n1->backupHHat < n2->backupHHat;
        }

        static double getLowerConfidence(const shared_ptr<Node> n)
        {
            double f    = n->getFValue();
            double mean = n->getFHatValue();
            if (f == mean) {
                return f;
            }
            double error  = mean - f;
            double stdDev = error / 2.0;
            double var    = pow(stdDev, 2);
            // 1.96 is the Z value from the Z table to get the 2.5 confidence
            return max(f, mean - (1.96 * var));
        }

        static bool compareNodesLC(const shared_ptr<Node> n1,
                                   const shared_ptr<Node> n2)
        {
            // Lower confidence interval
            if (getLowerConfidence(n1) == getLowerConfidence(n2)) {
                return n1->getGValue() > n2->getGValue();
            }
            return getLowerConfidence(n1) < getLowerConfidence(n2);
        }
    };

    RealTimeSearch(Domain& domain_, string decisionModule_, size_t lookahead_)
        : domain(domain_)
        , lookahead(lookahead_)
        , decisionModule(decisionModule_)
    {
        if (decisionModule == "one" || decisionModule == "alltheway") {
            metaReasonDecisionAlgo =
              make_shared<MetaReasonScalarBackup<Domain, Node>>(
                decisionModule_);
        } else if (decisionModule == "dtrts") {
            metaReasonDecisionAlgo =
              make_shared<MetaReasonNancyBackup<Domain, Node>>(decisionModule_,
                                                               domain, lookahead);
        } else {
            cerr << "unknown decision module: " << decisionModule << "\n";
            exit(1);
        }

        metaReasonExpansionAlgo =
          make_shared<MetaReasonAStar<Domain, Node>>(domain, lookahead, "f");

        metaReasonLearningAlgo =
          make_shared<MetaReasonDijkstra<Domain, Node>>(domain);
    }

    ~RealTimeSearch() { clean(); }

    // p: iterationlimit
    ResultContainer search()
    {
        ResultContainer res;

        shared_ptr<Node> initNode = make_shared<Node>(
          0, domain.heuristic(domain.getStartState()),
          domain.distance(domain.getStartState()),
          domain.distanceErr(domain.getStartState()), domain.epsilonHGlobal(),
          domain.epsilonDGlobal(), domain.getStartState(), nullptr);

        int count = 0;

        queue<shared_ptr<Node>> actionQueue;
        actionQueue.push(initNode);

        // if set a cutoff iteration
        // while (count <= iterationlimit) {
        while (1) {
            auto start = actionQueue.front();

            if (decisionModule == "alltheway") {
                vector<string> curPath;
                while (actionQueue.size() > 1) {

                    start = actionQueue.front();
                    actionQueue.pop();
                    curPath.push_back(start->getState().toString());
                    // TODO cost can not be computed here
                    // res.solutionCost += n->getGValue();
                    res.solutionLength += 1;

                    // lsslrta* try to optimize cpu time,
                    // so even if more than one action are commited, it
                    // will not use the time to thinking,
                    // so we have to directly advance the "time"
                    res.GATnodesExpanded += lookahead;

                    if (domain.isGoal(start->getState())) {
                        return res;
                    }
                }
                if (!curPath.empty()) {
                    curPath.push_back(
                      actionQueue.front()->getState().toString());
                    res.paths.push_back(curPath);
                }

                start = actionQueue.front();
            }

            // Check if a goal has been reached
            if (domain.isGoal(start->getState())) {
                res.solutionFound = true;
                // vector<string> curPath;
                // curPath.push_back(start->getState().toString());
                // res.paths.push_back(curPath);

                res.solutionLength += 1;

                return res;
            }

            restartLists(start);

            domain.updateEpsilons();

            // Expansion and Decision-making Phase
            // check how many of the prefix should be commit
            stack<shared_ptr<Node>> commitQueue;

            // four metaReasoningDecisionAlgo
            // 1. allways commit one, just like old nancy code
            // 2. allways commit to frontier,  modify old nancy code
            //    to return all nodes from root to the best frontier
            // 3. fhat-pmr: need nancy backup from all frontier and
            //    make decision on whether to commit each prefix based
            //    on the hack rule
            // 4. our approach: compute benefit of doing more search

            // this loop should happen only once for approach 1-3
            while (commitQueue.empty() && !actionQueue.empty()) {
                // do more search
                metaReasonExpansionAlgo->expand(open, closed,
                                                duplicateDetection, res);
                // deadend
                if (open.empty()) {
                    break;
                }

                // meta-reason about how much to commit
                commitQueue = metaReasonDecisionAlgo->backup(
                  open, start, closed, false);

                DEBUG_MSG("commit size: " << commitQueue.size());

                auto n = actionQueue.front();
                actionQueue.pop();
                if (decisionModule != "alltheway") {
                    vector<string> curPath;
                    curPath.push_back(n->getState().toString());
                    res.paths.push_back(curPath);
                }
                // TODO cost can not be computed here
                // res.solutionCost += n->getGValue();
                res.solutionLength += 1;
            }

            // deadend
            if (open.empty()) {
                break;
            }

            // if action queue is empty and metareasoning do not want to commit
            // force to commit at least one action
            if (commitQueue.empty()) {
                // force to commit at least one action
                commitQueue = metaReasonDecisionAlgo->backup(
                  open, start, closed, true);
            }

            assert(commitQueue.size() > 0);

            while (!commitQueue.empty()) {
                auto n = commitQueue.top();
                commitQueue.pop();
                actionQueue.push(n);
            }

            // LearninH Phase
            metaReasonLearningAlgo->learn(open, closed);

            ++count;
            DEBUG_MSG("iteration: " << count);
        }

        return res;
    }

private:
    static bool duplicateDetection(
      shared_ptr<Node>                              node,
      unordered_map<State, shared_ptr<Node>, Hash>& closed,
      PriorityQueue<shared_ptr<Node>>&              open)
    {
        // Check if this state exists
        typename unordered_map<State, shared_ptr<Node>, Hash>::iterator it =
          closed.find(node->getState());

        if (it != closed.end()) {
            // This state has been generated before, check if its node is on
            // OPEN
            if (it->second->onOpen()) {
                // This node is on OPEN, keep the better g-value
                if (node->getGValue() < it->second->getGValue()) {
                    it->second->setGValue(node->getGValue());
                    it->second->setParent(node->getParent());
                    it->second->setHValue(node->getHValue());
                    it->second->setDValue(node->getDValue());
                    it->second->setDErrValue(node->getDErrValue());
                    it->second->setEpsilonH(node->getEpsilonH());
                    it->second->setEpsilonD(node->getEpsilonD());
                    it->second->setState(node->getState());
                    open.update(it->second);
                }
            } else {
                // This node is on CLOSED, compare the f-values. If this new
                // f-value is better, reset g, h, and d.
                // Then reopen the node.
                if (node->getFValue() < it->second->getFValue()) {
                    it->second->setGValue(node->getGValue());
                    it->second->setParent(node->getParent());
                    it->second->setHValue(node->getHValue());
                    it->second->setDValue(node->getDValue());
                    it->second->setDErrValue(node->getDErrValue());
                    it->second->setEpsilonH(node->getEpsilonH());
                    it->second->setEpsilonD(node->getEpsilonD());
                    it->second->setState(node->getState());
                    it->second->reOpen();
                    open.push(it->second);
                }
            }

            return true;
        }

        return false;
    }

    void restartLists(shared_ptr<Node> start)
    {
        // mark this node as the start of the current search (to
        // prevent state pruning based on label)
        start->markStart();

        // Empty OPEN and CLOSED
        open.clear();

        // delete all of the nodes from the last expansion phase
        closed.clear();

        // reset start g as 0
        start->setGValue(0);

        start->setParent(nullptr);

        open.push(start);
    }

    void clean()
    {
        // Empty OPEN and CLOSED
        open.clear();

        // delete all of the nodes from the last expansion phase
        closed.clear();
    }

    void noSolutionFound(ResultContainer& res)
    {
        res.solutionFound = false;
        res.solutionCost  = -1;
    }

protected:
    Domain&                                      domain;
    shared_ptr<DecisionAlgorithm<Domain, Node>>  metaReasonDecisionAlgo;
    shared_ptr<MetaReasonAStar<Domain, Node>>    metaReasonExpansionAlgo;
    shared_ptr<MetaReasonDijkstra<Domain, Node>> metaReasonLearningAlgo;
    PriorityQueue<shared_ptr<Node>>              open;
    unordered_map<State, shared_ptr<Node>, Hash> closed;

    size_t lookahead;
    string decisionModule;
};
