import { useState } from "react";
import { Button, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import GroupsIcon from "@mui/icons-material/Groups";
import HomeIcon from "@mui/icons-material/Home";

import { useActiveHousehold } from "../../hooks/useActiveHousehold";
import { useHouseholds } from "./hooks";

export function HouseholdSwitcher() {
  const { data: households = [] } = useHouseholds();
  const { activeHouseholdId, setActiveHouseholdId } = useActiveHousehold();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const activeName =
    activeHouseholdId === null
      ? "Personal"
      : (households.find((h) => h.id === activeHouseholdId)?.name ?? "Personal");

  return (
    <>
      <Button
        color="inherit"
        startIcon={activeHouseholdId ? <GroupsIcon /> : <HomeIcon />}
        onClick={(event) => setAnchorEl(event.currentTarget)}
      >
        {activeName}
      </Button>
      <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}>
        <MenuItem
          selected={activeHouseholdId === null}
          onClick={() => {
            setActiveHouseholdId(null);
            setAnchorEl(null);
          }}
        >
          <ListItemIcon>
            {activeHouseholdId === null ? <CheckIcon fontSize="small" /> : <HomeIcon fontSize="small" />}
          </ListItemIcon>
          <ListItemText>Personal</ListItemText>
        </MenuItem>
        {households.map((household) => (
          <MenuItem
            key={household.id}
            selected={activeHouseholdId === household.id}
            onClick={() => {
              setActiveHouseholdId(household.id);
              setAnchorEl(null);
            }}
          >
            <ListItemIcon>
              {activeHouseholdId === household.id ? (
                <CheckIcon fontSize="small" />
              ) : (
                <GroupsIcon fontSize="small" />
              )}
            </ListItemIcon>
            <ListItemText>{household.name}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
