# GitHub Discussions Setup

Enable Discussions and configure community categories for the 3we Robot Platform.

## Prerequisites

- Repository admin access
- `gh` CLI authenticated (`gh auth login`)

## Enable Discussions

```bash
# Enable via GitHub API
gh api repos/{owner}/{repo} -X PATCH -f has_discussions=true
```

Or: **Settings** > **General** > **Features** > check **Discussions**.

## Create Categories

After enabling Discussions, create the required categories:

```bash
REPO="3we-robotics/3we-robot-platform"  # adjust to your org/repo

# Get the repository node ID
REPO_ID=$(gh api graphql -f query='{ repository(owner:"3we-robotics", name:"3we-robot-platform") { id } }' --jq '.data.repository.id')

# Create categories via GraphQL
for category in \
  '{"name":"General","emoji":":speech_balloon:","description":"General discussion about the platform","isAnswerable":false}' \
  '{"name":"Help / Q&A","emoji":":raising_hand:","description":"Ask questions and get help from the community","isAnswerable":true}' \
  '{"name":"Paper Discussion","emoji":":page_facing_up:","description":"Discuss the research paper, benchmarks, and Sim2Real results","isAnswerable":false}' \
  '{"name":"Show and Tell","emoji":":star2:","description":"Share your projects, demos, and modifications","isAnswerable":false}' \
  '{"name":"Ideas / RFCs","emoji":":bulb:","description":"Propose new features or architectural changes","isAnswerable":false}'; do

  NAME=$(echo "$category" | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])")
  EMOJI=$(echo "$category" | python3 -c "import json,sys; print(json.load(sys.stdin)['emoji'])")
  DESC=$(echo "$category" | python3 -c "import json,sys; print(json.load(sys.stdin)['description'])")
  ANSWERABLE=$(echo "$category" | python3 -c "import json,sys; print(str(json.load(sys.stdin)['isAnswerable']).lower())")

  gh api graphql -f query="
    mutation {
      createDiscussionCategory(input: {
        repositoryId: \"$REPO_ID\",
        name: \"$NAME\",
        emoji: \"$EMOJI\",
        description: \"$DESC\",
        isAnswerable: $ANSWERABLE
      }) { clientMutationId }
    }"
  echo "Created: $NAME"
done
```

## Expected Categories

| Category | Purpose | Answerable |
|----------|---------|:---:|
| General | Open-ended platform discussion | No |
| Help / Q&A | Community support, troubleshooting | Yes |
| Paper Discussion | Research paper, benchmarks, Sim2Real methodology | No |
| Show and Tell | Community projects and demos | No |
| Ideas / RFCs | Feature proposals and architecture discussions | No |

## Verification

```bash
# List categories after creation
gh api graphql -f query='
  { repository(owner:"3we-robotics", name:"3we-robot-platform") {
    discussionCategories(first:10) { nodes { name emoji isAnswerable } }
  } }' --jq '.data.repository.discussionCategories.nodes[]'
```

## Pinned Discussions (Optional)

After categories exist, create welcome posts:

```bash
# Create a pinned welcome discussion
gh api graphql -f query="
  mutation {
    createDiscussion(input: {
      repositoryId: \"$REPO_ID\",
      categoryId: \"<GENERAL_CATEGORY_ID>\",
      title: \"Welcome to 3we Discussions!\",
      body: \"Welcome! This is the community space for the 3we Robot Platform. Use **Help / Q&A** for questions, **Paper Discussion** for research topics, and **Show and Tell** to share your builds.\"
    }) { discussion { id } }
  }"
```
